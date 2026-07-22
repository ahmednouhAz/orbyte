from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.orm import Session

from orbyte.db.models import Persona__UserGroup
from orbyte.db.models import User__UserGroup
from orbyte.db.models import UserGroup
from orbyte.db.models import UserGroup__ConnectorCredentialPair
from orbyte.utils.logger import setup_logger

logger = setup_logger()


def fetch_user_group_by_id(db_session: Session, group_id: int) -> UserGroup | None:
    return db_session.scalar(select(UserGroup).where(UserGroup.id == group_id))


def user_curates_group(db_session: Session, user_id: UUID, group_id: int) -> bool:
    return (
        db_session.scalar(
            select(User__UserGroup).where(
                User__UserGroup.user_id == user_id,
                User__UserGroup.user_group_id == group_id,
                User__UserGroup.is_curator == True,  # noqa: E712
            )
        )
        is not None
    )


def fetch_user_groups(
    db_session: Session, include_default: bool = True
) -> Sequence[UserGroup]:
    stmt = select(UserGroup)
    if not include_default:
        stmt = stmt.where(UserGroup.is_default == False)  # noqa: E712
    return db_session.scalars(stmt).unique().all()


def fetch_minimal_user_groups(db_session: Session) -> Sequence[UserGroup]:
    """Same rows as `fetch_user_groups`; callers project down to id/name."""
    return fetch_user_groups(db_session, include_default=True)


def insert_user_group(
    db_session: Session,
    name: str,
    user_ids: list[UUID],
    cc_pair_ids: list[int],
) -> UserGroup:
    try:
        new_group = UserGroup(name=name, is_up_to_date=True)
        db_session.add(new_group)
        db_session.flush()  # assign an id

        for user_id in set(user_ids):
            db_session.add(
                User__UserGroup(user_group_id=new_group.id, user_id=user_id)
            )
        for cc_pair_id in set(cc_pair_ids):
            db_session.add(
                UserGroup__ConnectorCredentialPair(
                    user_group_id=new_group.id, cc_pair_id=cc_pair_id
                )
            )

        db_session.commit()
    except Exception as e:
        db_session.rollback()
        logger.error("Error creating user group: %s", e)
        raise

    return new_group


def update_user_group(
    db_session: Session,
    group_id: int,
    user_ids: list[UUID],
    cc_pair_ids: list[int],
    curator_ids: list[UUID] | None = None,
) -> UserGroup:
    group = fetch_user_group_by_id(db_session, group_id)
    if group is None:
        raise ValueError(f"No user group with ID '{group_id}'")

    # None means "caller isn't authorized to change curators" (see api.py) —
    # preserve the existing curator set rather than wiping it out.
    if curator_ids is None:
        curator_id_set = {
            row.user_id
            for row in db_session.scalars(
                select(User__UserGroup).where(
                    User__UserGroup.user_group_id == group_id,
                    User__UserGroup.is_curator == True,  # noqa: E712
                )
            ).all()
            if row.user_id is not None
        }
    else:
        curator_id_set = set(curator_ids)

    try:
        db_session.execute(
            delete(User__UserGroup).where(User__UserGroup.user_group_id == group_id)
        )
        for user_id in set(user_ids):
            db_session.add(
                User__UserGroup(
                    user_group_id=group_id,
                    user_id=user_id,
                    is_curator=user_id in curator_id_set,
                )
            )

        db_session.execute(
            delete(UserGroup__ConnectorCredentialPair).where(
                UserGroup__ConnectorCredentialPair.user_group_id == group_id
            )
        )
        for cc_pair_id in set(cc_pair_ids):
            db_session.add(
                UserGroup__ConnectorCredentialPair(
                    user_group_id=group_id, cc_pair_id=cc_pair_id
                )
            )

        db_session.commit()
    except Exception as e:
        db_session.rollback()
        logger.error("Error updating user group %s: %s", group_id, e)
        raise

    db_session.refresh(group)
    return group


def add_users_to_user_group(
    db_session: Session, group_id: int, user_ids: list[UUID]
) -> UserGroup:
    group = fetch_user_group_by_id(db_session, group_id)
    if group is None:
        raise ValueError(f"No user group with ID '{group_id}'")

    existing_user_ids = {
        row.user_id
        for row in db_session.scalars(
            select(User__UserGroup).where(User__UserGroup.user_group_id == group_id)
        ).all()
    }

    try:
        for user_id in set(user_ids):
            if user_id not in existing_user_ids:
                db_session.add(
                    User__UserGroup(user_group_id=group_id, user_id=user_id)
                )
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        logger.error("Error adding users to user group %s: %s", group_id, e)
        raise

    db_session.refresh(group)
    return group


def rename_user_group(db_session: Session, group_id: int, new_name: str) -> UserGroup:
    group = fetch_user_group_by_id(db_session, group_id)
    if group is None:
        raise ValueError(f"No user group with ID '{group_id}'")

    try:
        group.name = new_name
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        logger.error("Error renaming user group %s: %s", group_id, e)
        raise

    return group


def delete_user_group(db_session: Session, group: UserGroup) -> None:
    if group.is_default:
        raise ValueError("Cannot delete a default user group")

    try:
        db_session.execute(
            delete(User__UserGroup).where(
                User__UserGroup.user_group_id == group.id
            )
        )
        db_session.execute(
            delete(UserGroup__ConnectorCredentialPair).where(
                UserGroup__ConnectorCredentialPair.user_group_id == group.id
            )
        )
        db_session.execute(
            delete(Persona__UserGroup).where(
                Persona__UserGroup.user_group_id == group.id
            )
        )
        db_session.delete(group)
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        logger.error("Error deleting user group %s: %s", group.id, e)
        raise


def update_group_agent_sharing(
    db_session: Session,
    group_id: int,
    added_agent_ids: list[int],
    removed_agent_ids: list[int],
) -> None:
    try:
        if removed_agent_ids:
            db_session.execute(
                delete(Persona__UserGroup).where(
                    Persona__UserGroup.user_group_id == group_id,
                    Persona__UserGroup.persona_id.in_(removed_agent_ids),
                )
            )

        existing_persona_ids = {
            row.persona_id
            for row in db_session.scalars(
                select(Persona__UserGroup).where(
                    Persona__UserGroup.user_group_id == group_id,
                    Persona__UserGroup.persona_id.in_(added_agent_ids),
                )
            ).all()
        }
        for persona_id in added_agent_ids:
            if persona_id not in existing_persona_ids:
                db_session.add(
                    Persona__UserGroup(
                        persona_id=persona_id, user_group_id=group_id
                    )
                )

        db_session.commit()
    except Exception as e:
        db_session.rollback()
        logger.error(
            "Error updating agent sharing for user group %s: %s", group_id, e
        )
        raise
