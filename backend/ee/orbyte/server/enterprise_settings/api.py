from fastapi import APIRouter

from ee.orbyte.server.enterprise_settings.models import EnterpriseSettings
from ee.orbyte.server.enterprise_settings.store import load_settings
from orbyte.server.utils import BasicAuthenticationError
from orbyte.utils.logger import setup_logger
from shared_configs.configs import MULTI_TENANT
from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA
from shared_configs.contextvars import get_current_tenant_id

basic_router = APIRouter(prefix="/enterprise-settings")

logger = setup_logger()


@basic_router.get("")
def ee_fetch_settings() -> EnterpriseSettings:
    if MULTI_TENANT:
        tenant_id = get_current_tenant_id()
        if not tenant_id or tenant_id == POSTGRES_DEFAULT_SCHEMA:
            raise BasicAuthenticationError(detail="User must authenticate")

    return load_settings()
