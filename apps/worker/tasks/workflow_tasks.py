from __future__ import annotations

from apps.worker.celery_app import celery_app


def _run_workflow(run_id: str) -> None:
    from apps.api.deps import get_workflow_service

    get_workflow_service().execute_run(run_id)


if celery_app is not None:
    @celery_app.task(name='workflow.execute_run')
    def execute_workflow_run(run_id: str) -> None:
        _run_workflow(run_id)
else:
    def execute_workflow_run(run_id: str) -> None:
        _run_workflow(run_id)


def dispatch_workflow_run(run_id: str) -> None:
    if celery_app is not None and hasattr(execute_workflow_run, 'delay'):
        execute_workflow_run.delay(run_id)
    else:
        _run_workflow(run_id)
