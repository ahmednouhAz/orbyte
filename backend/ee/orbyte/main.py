from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ee.orbyte.server.analytics.api import router as analytics_router
from ee.orbyte.server.auth_check import check_ee_router_auth
from ee.orbyte.server.documents.cc_pair import router as ee_document_cc_pair_router
from ee.orbyte.server.enterprise_settings.api import (
    basic_router as enterprise_settings_router,
)
from ee.orbyte.server.evals.api import router as evals_router
from ee.orbyte.server.manage.standard_answer import router as standard_answer_router
from ee.orbyte.server.middleware.license_enforcement import (
    add_license_enforcement_middleware,
)
from ee.orbyte.server.middleware.tenant_tracking import (
    add_api_server_tenant_id_middleware,
)
from ee.orbyte.server.middleware.tier_gate import add_tier_gate_middleware
from ee.orbyte.server.oauth.api import router as ee_oauth_router
from ee.orbyte.server.query_and_chat.query_backend import basic_router as ee_query_router
from ee.orbyte.server.query_and_chat.search_backend import router as search_router
from ee.orbyte.server.query_history.api import router as query_history_router
from ee.orbyte.server.reporting.usage_export_api import router as usage_export_router
from ee.orbyte.server.seeding import seed_db
from ee.orbyte.server.tenants.api import router as tenants_router
from ee.orbyte.server.token_rate_limits.api import (
    router as token_rate_limit_settings_router,
)
from ee.orbyte.server.user_group.api import router as user_group_router
from ee.orbyte.utils.encryption import test_encryption
from orbyte.main import get_application as get_application_base
from orbyte.main import include_router_with_global_prefix_prepended
from orbyte.main import lifespan as lifespan_base
from orbyte.main import use_route_function_names_as_operation_ids
from orbyte.server.query_and_chat.query_backend import basic_router as query_router
from orbyte.utils.logger import setup_logger
from orbyte.utils.variable_functionality import global_version
from shared_configs.configs import MULTI_TENANT

logger = setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Small wrapper around the lifespan of the MIT application.
    Basically just calls the base lifespan, and then adds EE-only
    steps after."""

    async with lifespan_base(app):
        # seed the Orbyte environment with LLMs, Assistants, etc. based on an optional
        # environment variable. Used to automate deployment for multiple environments.
        seed_db()

        yield


def get_application() -> FastAPI:
    # Anything that happens at import time is not guaranteed to be running ee-version
    # Anything after the server startup will be running ee version
    global_version.set_ee()

    test_encryption()

    application = get_application_base(lifespan_override=lifespan)

    # Register tier_gate FIRST so it becomes the innermost middleware: Starlette
    # executes middleware in reverse registration order, and tier_gate must run
    # AFTER tenant_tracking has populated CURRENT_TENANT_ID_CONTEXTVAR.
    # Tier gate attaches in both modes; get_tier() resolves per deployment
    # internally. Reads the unified PATH_PREFIX_MIN_TIER map.
    add_tier_gate_middleware(application, logger)

    if MULTI_TENANT:
        add_api_server_tenant_id_middleware(application, logger)
    else:
        # License enforcement middleware for self-hosted deployments only
        # Checks LICENSE_ENFORCEMENT_ENABLED at runtime (can be toggled without restart)
        # MT deployments use control plane gating via is_tenant_gated() instead
        add_license_enforcement_middleware(application, logger)

    # NOTE: Google OAuth / OIDC / SAML login and billing/license routers have
    # been removed — this deployment is Basic (local email/password) auth
    # only. See orbyte/main.py for the auth router registration.

    # RBAC / group access control
    include_router_with_global_prefix_prepended(application, user_group_router)
    # Analytics endpoints
    include_router_with_global_prefix_prepended(application, analytics_router)
    include_router_with_global_prefix_prepended(application, query_history_router)
    # EE only backend APIs
    include_router_with_global_prefix_prepended(application, query_router)
    include_router_with_global_prefix_prepended(application, ee_query_router)
    include_router_with_global_prefix_prepended(application, search_router)
    include_router_with_global_prefix_prepended(application, standard_answer_router)
    include_router_with_global_prefix_prepended(application, ee_oauth_router)
    include_router_with_global_prefix_prepended(application, ee_document_cc_pair_router)
    include_router_with_global_prefix_prepended(application, evals_router)

    # Enterprise-only global settings (application_name branding fallback only —
    # whitelabel admin UI/logo upload/custom-analytics-script removed)
    include_router_with_global_prefix_prepended(application, enterprise_settings_router)
    # Token rate limit settings
    include_router_with_global_prefix_prepended(
        application, token_rate_limit_settings_router
    )
    include_router_with_global_prefix_prepended(application, usage_export_router)

    if MULTI_TENANT:
        # Tenant management
        include_router_with_global_prefix_prepended(application, tenants_router)

    # Ensure all routes have auth enabled or are explicitly marked as public
    check_ee_router_auth(application)

    # for debugging discovered routes
    # for route in application.router.routes:
    #     print(f"Path: {route.path}, Methods: {route.methods}")

    use_route_function_names_as_operation_ids(application)

    return application
