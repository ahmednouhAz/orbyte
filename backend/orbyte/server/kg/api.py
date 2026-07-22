from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from orbyte.auth.permissions import require_permission
from orbyte.configs.constants import TMP_DRALPHA_PERSONA_NAME
from orbyte.configs.kg_configs import KG_BETA_ASSISTANT_DESCRIPTION
from orbyte.db.engine.sql_engine import get_session
from orbyte.db.entities import get_entity_stats_by_grounded_source_name
from orbyte.db.entity_type import get_configured_entity_types
from orbyte.db.entity_type import update_entity_types_and_related_connectors__commit
from orbyte.db.enums import Permission
from orbyte.db.kg_config import disable_kg
from orbyte.db.kg_config import enable_kg
from orbyte.db.kg_config import get_kg_config_settings
from orbyte.db.kg_config import set_kg_config_settings
from orbyte.db.models import User
from orbyte.db.persona import create_update_persona
from orbyte.db.persona import get_persona_by_id
from orbyte.db.persona import mark_persona_as_deleted
from orbyte.db.persona import mark_persona_as_not_deleted
from orbyte.db.tools import get_builtin_tool
from orbyte.kg.resets.reset_index import reset_full_kg_index__commit
from orbyte.kg.setup.kg_default_entity_definitions import (
    populate_missing_default_entity_types__commit,
)
from orbyte.prompts.kg_prompts import KG_BETA_ASSISTANT_SYSTEM_PROMPT
from orbyte.prompts.kg_prompts import KG_BETA_ASSISTANT_TASK_PROMPT
from orbyte.server.features.persona.models import PersonaUpsertRequest
from orbyte.server.kg.models import DisableKGConfigRequest
from orbyte.server.kg.models import EnableKGConfigRequest
from orbyte.server.kg.models import EntityType
from orbyte.server.kg.models import KGConfig
from orbyte.server.kg.models import KGConfig as KGConfigAPIModel
from orbyte.server.kg.models import SourceAndEntityTypeView
from orbyte.server.kg.models import SourceStatistics
from orbyte.tools.tool_implementations.search.search_tool import SearchTool

admin_router = APIRouter(prefix="/admin/kg")


# exposed
# Controls whether or not kg is viewable in the first place.


@admin_router.get("/exposed")
def get_kg_exposed(
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
) -> bool:
    kg_config_settings = get_kg_config_settings()
    return kg_config_settings.KG_EXPOSED


# global resets


@admin_router.put("/reset")
def reset_kg(
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    db_session: Session = Depends(get_session),
) -> SourceAndEntityTypeView:
    reset_full_kg_index__commit(db_session)
    populate_missing_default_entity_types__commit(db_session=db_session)
    return get_kg_entity_types(db_session=db_session)


# configurations


@admin_router.get("/config")
def get_kg_config(
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
) -> KGConfig:
    config = get_kg_config_settings()
    return KGConfigAPIModel.from_kg_config_settings(config)


@admin_router.put("/config")
def enable_or_disable_kg(
    req: EnableKGConfigRequest | DisableKGConfigRequest,
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    db_session: Session = Depends(get_session),
) -> None:
    if isinstance(req, DisableKGConfigRequest):
        # Get the KG Beta persona ID and delete it
        kg_config_settings = get_kg_config_settings()
        persona_id = kg_config_settings.KG_BETA_PERSONA_ID
        if persona_id is not None:
            mark_persona_as_deleted(
                persona_id=persona_id,
                user=user,
                db_session=db_session,
            )
        disable_kg()
        return

    # Enable KG
    enable_kg(enable_req=req)
    populate_missing_default_entity_types__commit(db_session=db_session)

    # Get the search tool. The Knowledge Graph tool itself is dead code
    # (its construction path is disabled in tool_constructor.py) and has been
    # removed, so the KG Beta persona below is search-only.
    search_tool = get_builtin_tool(db_session=db_session, tool_type=SearchTool)

    # Check if we have a previously created persona
    kg_config_settings = get_kg_config_settings()
    persona_id = kg_config_settings.KG_BETA_PERSONA_ID

    if persona_id is not None:
        # Try to restore the existing persona
        try:
            persona = get_persona_by_id(
                persona_id=persona_id,
                user=user,
                db_session=db_session,
                include_deleted=True,
            )
            if persona.deleted:
                mark_persona_as_not_deleted(
                    persona_id=persona_id,
                    user=user,
                    db_session=db_session,
                )
            return

        except ValueError:
            # If persona doesn't exist or can't be restored, create a new one below
            pass

    # Create KG Beta persona (private to the admin who enabled KG)
    persona_request = PersonaUpsertRequest(
        name=TMP_DRALPHA_PERSONA_NAME,
        description=KG_BETA_ASSISTANT_DESCRIPTION,
        system_prompt=KG_BETA_ASSISTANT_SYSTEM_PROMPT,
        task_prompt=KG_BETA_ASSISTANT_TASK_PROMPT,
        datetime_aware=False,
        is_public=False,
        document_set_ids=[],
        tool_ids=[search_tool.id],
        starter_messages=None,
        users=[user.id],
        groups=[],
        label_ids=[],
        is_featured=False,
        display_priority=0,
        user_file_ids=[],
        default_model_configuration_id=None,
    )

    persona_snapshot = create_update_persona(
        persona_id=None,
        create_persona_request=persona_request,
        user=user,
        db_session=db_session,
    )
    # Store the persona ID in the KG config
    kg_config_settings.KG_BETA_PERSONA_ID = persona_snapshot.id
    set_kg_config_settings(kg_config_settings)


# entity-types


@admin_router.get("/entity-types")
def get_kg_entity_types(
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    db_session: Session = Depends(get_session),
) -> SourceAndEntityTypeView:
    # when using for the first time, populate with default entity types
    entity_types = {
        source_name: [EntityType.from_model(et) for et in ets]
        for source_name, ets in get_configured_entity_types(
            db_session=db_session
        ).items()
    }

    source_statistics = {
        source_name: SourceStatistics(
            source_name=source_name,
            last_updated=last_updated,
            entities_count=entities_count,
        )
        for source_name, (
            last_updated,
            entities_count,
        ) in get_entity_stats_by_grounded_source_name(db_session=db_session).items()
    }

    return SourceAndEntityTypeView(
        source_statistics=source_statistics, entity_types=entity_types
    )


@admin_router.put("/entity-types")
def update_kg_entity_types(
    updates: list[EntityType],
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    db_session: Session = Depends(get_session),
) -> None:
    update_entity_types_and_related_connectors__commit(
        db_session=db_session, updates=updates
    )
