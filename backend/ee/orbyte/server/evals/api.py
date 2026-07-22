from fastapi import APIRouter
from fastapi import Depends

from ee.orbyte.auth.users import current_cloud_superuser
from orbyte.background.celery.apps.client import celery_app as client_app
from orbyte.configs.constants import OrbyteCeleryTask
from orbyte.db.models import User
from orbyte.evals.models import EvalConfigurationOptions
from orbyte.server.evals.models import EvalRunAck
from orbyte.utils.logger import setup_logger

logger = setup_logger()

router = APIRouter(prefix="/evals")


@router.post("/eval_run", response_model=EvalRunAck)
def eval_run(
    request: EvalConfigurationOptions,
    user: User = Depends(current_cloud_superuser),  # noqa: ARG001
) -> EvalRunAck:
    """
    Run an evaluation with the given message and optional dataset.
    This endpoint requires a valid API key for authentication.
    """
    client_app.send_task(
        OrbyteCeleryTask.EVAL_RUN_TASK,
        kwargs={
            "configuration_dict": request.model_dump(),
        },
    )
    return EvalRunAck(success=True)
