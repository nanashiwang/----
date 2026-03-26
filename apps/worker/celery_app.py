from __future__ import annotations

try:
    from celery import Celery
except Exception:  # pragma: no cover - optional runtime dependency
    Celery = None

from core.config import get_settings

settings = get_settings()
celery_app = None
if Celery is not None:
    celery_app = Celery(
        'quant_platform_worker',
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )
    celery_app.conf.task_track_started = True
    celery_app.conf.task_serializer = 'json'
    celery_app.conf.result_serializer = 'json'
    celery_app.conf.accept_content = ['json']
