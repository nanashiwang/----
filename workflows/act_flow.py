from __future__ import annotations

from core.enums import RunStatus
from domain.schemas import FlowState
from workflows.base import BaseFlowRunner


class ActFlowRunner(BaseFlowRunner):
    flow_name = 'act'
    node_sequence = (
        'upload_settlement_image',
        'parse_trade_with_ocr',
        'wait_user_confirmation',
        'save_trade_record',
    )

    def upload_settlement_image(self, state: FlowState) -> FlowState:
        state.metadata['settlement_image_uri'] = state.payload.get('image_uri', state.metadata.get('settlement_image_uri', ''))
        return state

    def parse_trade_with_ocr(self, state: FlowState) -> FlowState:
        if state.trade_ocr is not None:
            return state
        image_uri = state.metadata.get('settlement_image_uri', '')
        state.trade_ocr = self.deps.ocr_service.parse(image_uri)
        return state

    def wait_user_confirmation(self, state: FlowState) -> FlowState:
        if state.user_confirmation is True:
            return state
        state.status = RunStatus.WAITING_FOR_USER
        return state

    def save_trade_record(self, state: FlowState) -> FlowState:
        if state.trade_ocr is None:
            state.status = RunStatus.FAILED
            state.errors.append({'message': 'trade_ocr is missing before save_trade_record'})
            return state
        symbol = state.trade_ocr.symbol or state.payload.get('symbol') or 'UNKNOWN'
        trade_date = state.trade_ocr.trade_date or state.as_of_date
        self.deps.trade_repository.create(
            run_id=state.run_id,
            recommendation_id=state.payload.get('recommendation_id'),
            recommendation_run_id=state.payload.get('recommendation_run_id'),
            symbol=symbol,
            trade_date=trade_date,
            action=state.trade_ocr.side or state.payload.get('side', 'buy'),
            price=state.trade_ocr.price or float(state.payload.get('price', 0.0) or 0.0),
            quantity=state.trade_ocr.quantity or int(state.payload.get('quantity', 0) or 0),
            fees=state.trade_ocr.fees,
            screenshot_uri=state.trade_ocr.image_uri,
            ocr_raw_json=state.trade_ocr.model_dump(mode='json'),
            confirmation_json={'confirmed': True},
        )
        return state
