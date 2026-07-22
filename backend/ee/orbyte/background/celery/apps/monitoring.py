from orbyte.background.celery.apps import app_base
from orbyte.background.celery.apps.monitoring import celery_app

celery_app.autodiscover_tasks(
    app_base.filter_task_modules(
        [
            "ee.orbyte.background.celery.tasks.tenant_provisioning",
        ]
    )
)
