from celery import Celery

import orbyte.background.celery.apps.app_base as app_base

celery_app = Celery(__name__)
celery_app.config_from_object("orbyte.background.celery.configs.client")
celery_app.Task = app_base.TenantAwareTask  # ty: ignore[invalid-assignment]
