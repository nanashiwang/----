from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from apps.api.deps import build_workflow_dependencies, get_workflow_service
from apps.api.responses import ApiResponse
from core.enums import FlowType
from domain.schemas import WorkflowTriggerIn

router = APIRouter(prefix='/api/trades', tags=['trades'])


@router.post('/upload-settlement', response_model=ApiResponse)
async def upload_settlement(
    file: UploadFile | None = File(default=None),
    run_id: str | None = Form(default=None),
    as_of_date: str | None = Form(default=None),
    recommendation_id: str | None = Form(default=None),
    recommendation_run_id: str | None = Form(default=None),
    confirmed: bool = Form(default=False),
):
    service = get_workflow_service()
    if run_id:
        run = service.resume_act_run(run_id, confirmed=confirmed)
        raw_run = build_workflow_dependencies().workflow_runs.get(run_id)
        return ApiResponse(data={'run': run, 'trade_ocr': raw_run.output_json.get('trade_ocr') if raw_run else None})

    if file is None or as_of_date is None:
        raise HTTPException(status_code=400, detail='file and as_of_date are required for a new act run')

    upload_dir = Path('data/uploads')
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or 'settlement.png').suffix or '.png'
    temp_file = tempfile.NamedTemporaryFile(delete=False, dir=upload_dir, suffix=suffix)
    temp_file.write(await file.read())
    temp_file.close()

    trigger = WorkflowTriggerIn(
        flow_type=FlowType.ACT,
        as_of_date=as_of_date,
        payload={
            'image_uri': temp_file.name,
            'recommendation_id': recommendation_id,
            'recommendation_run_id': recommendation_run_id,
            'user_confirmation': confirmed,
        },
    )
    run = service.trigger_workflow(trigger, async_mode=False)
    raw_run = build_workflow_dependencies().workflow_runs.get(run.run_id)
    return ApiResponse(data={'run': run, 'trade_ocr': raw_run.output_json.get('trade_ocr') if raw_run else None})
