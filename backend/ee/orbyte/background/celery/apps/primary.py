from orbyte.background.celery.apps import app_base
from orbyte.background.celery.apps.primary import celery_app

celery_app.autodiscover_tasks(
    app_base.filter_task_modules(
        [
            "ee.orbyte.background.celery.tasks.hooks",
            "ee.orbyte.background.celery.tasks.doc_permission_syncing",
            "ee.orbyte.background.celery.tasks.external_group_syncing",
            "ee.orbyte.background.celery.tasks.cloud",
            "ee.orbyte.background.celery.tasks.ttl_management",
            "ee.orbyte.background.celery.tasks.usage_reporting",
            "ee.orbyte.background.celery.tasks.license_notifications",
        ]
    )
)
