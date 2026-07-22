from orbyte.background.celery.apps import app_base
from orbyte.background.celery.apps.heavy import celery_app

celery_app.autodiscover_tasks(
    app_base.filter_task_modules(
        [
            "ee.orbyte.background.celery.tasks.doc_permission_syncing",
            "ee.orbyte.background.celery.tasks.external_group_syncing",
            "ee.orbyte.background.celery.tasks.cleanup",
            "ee.orbyte.background.celery.tasks.query_history",
        ]
    )
)
