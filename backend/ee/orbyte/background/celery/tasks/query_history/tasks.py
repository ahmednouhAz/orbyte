import csv
import io
from datetime import datetime

from celery import shared_task
from celery import Task

from ee.orbyte.server.query_history.api import fetch_and_process_chat_session_history
from ee.orbyte.server.query_history.api import ORBYTE_ANONYMIZED_EMAIL
from ee.orbyte.server.query_history.models import QuestionAnswerPairSnapshot
from orbyte.background.task_utils import construct_query_history_report_name
from orbyte.configs.app_configs import JOB_TIMEOUT
from orbyte.configs.constants import FileOrigin
from orbyte.configs.constants import FileType
from orbyte.configs.constants import OrbyteCeleryTask
from orbyte.configs.constants import QueryHistoryType
from orbyte.db.engine.sql_engine import get_session_with_current_tenant
from orbyte.db.tasks import delete_task_with_id
from orbyte.db.tasks import mark_task_as_finished_with_id
from orbyte.db.tasks import mark_task_as_started_with_id
from orbyte.file_store.file_store import get_default_file_store
from orbyte.server.settings.store import load_settings
from orbyte.utils.csv_utils import sanitize_csv_row
from orbyte.utils.logger import setup_logger

logger = setup_logger()


@shared_task(
    name=OrbyteCeleryTask.EXPORT_QUERY_HISTORY_TASK,
    ignore_result=True,
    soft_time_limit=JOB_TIMEOUT,
    bind=True,
    trail=False,
)
def export_query_history_task(
    self: Task,
    *,
    start: datetime,
    end: datetime,
    start_time: datetime,
    # Need to include the tenant_id since the TenantAwareTask needs this
    tenant_id: str,  # noqa: ARG001
) -> None:
    if not self.request.id:
        raise RuntimeError("No task id defined for this task; cannot identify it")

    task_id = self.request.id
    stream = io.StringIO()
    writer = csv.DictWriter(
        stream,
        fieldnames=list(QuestionAnswerPairSnapshot.model_fields.keys()),
    )
    writer.writeheader()

    with get_session_with_current_tenant() as db_session:
        try:
            mark_task_as_started_with_id(
                db_session=db_session,
                task_id=task_id,
            )

            snapshot_generator = fetch_and_process_chat_session_history(
                db_session=db_session,
                start=start,
                end=end,
            )

            query_history_type = load_settings().query_history_type
            for snapshot in snapshot_generator:
                if query_history_type == QueryHistoryType.ANONYMIZED:
                    snapshot.user_email = ORBYTE_ANONYMIZED_EMAIL

                writer.writerows(
                    # Sanitize to prevent CSV/formula injection against
                    # whoever opens the export in a spreadsheet (ON-008).
                    sanitize_csv_row(qa_pair.to_json())
                    for qa_pair in QuestionAnswerPairSnapshot.from_chat_session_snapshot(
                        snapshot
                    )
                )

        except Exception:
            logger.exception("Failed to export query history with task_id=%r", task_id)
            mark_task_as_finished_with_id(
                db_session=db_session,
                task_id=task_id,
                success=False,
            )
            raise

    report_name = construct_query_history_report_name(task_id)
    with get_session_with_current_tenant() as db_session:
        try:
            stream.seek(0)
            get_default_file_store().save_file(
                content=stream,
                display_name=report_name,
                file_origin=FileOrigin.QUERY_HISTORY_CSV,
                file_type=FileType.CSV,
                file_metadata={
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "start_time": start_time.isoformat(),
                },
                file_id=report_name,
            )

            delete_task_with_id(
                db_session=db_session,
                task_id=task_id,
            )
        except Exception:
            logger.exception(
                "Failed to save query history export file; report_name=%r", report_name
            )
            mark_task_as_finished_with_id(
                db_session=db_session,
                task_id=task_id,
                success=False,
            )
            raise
