from __future__ import annotations

from typing import Callable, Optional

from core.enums import FlowType, RunStatus
from core.ids import generate_prefixed_id
from domain.schemas import (
    CandidateOut,
    ColdKnowledge,
    EvidenceRef,
    FlowState,
    HotKnowledgeOut,
    KnowledgeItem,
    RecommendationRecordOut,
    ReviewReportOut,
    ReviewVerdict,
    TradeOCRResult,
    WorkflowRunOut,
    WorkflowTriggerIn,
)
from workflows.factory import build_flow_runner


class WorkflowApplicationService:
    def __init__(self, deps_factory: Callable[[], object], async_dispatcher: Optional[Callable[[str], None]] = None):
        self._deps_factory = deps_factory
        self._async_dispatcher = async_dispatcher

    def trigger_workflow(self, trigger: WorkflowTriggerIn, async_mode: bool = True) -> WorkflowRunOut:
        deps = self._deps_factory()
        if trigger.flow_type is None:
            raise ValueError('flow_type is required before triggering a workflow')
        idempotency_key = self._build_idempotency_key(trigger)
        if trigger.flow_type == FlowType.OBSERVE and not trigger.force:
            existing = deps.workflow_runs.get_by_idempotency_key(idempotency_key)
            if existing is not None:
                return WorkflowRunOut.model_validate(existing)

        run = deps.workflow_runs.create(
            run_id=generate_prefixed_id(trigger.flow_type.value),
            flow_type=trigger.flow_type,
            status=RunStatus.PENDING,
            as_of_date=trigger.as_of_date,
            trigger_source=trigger.trigger_source,
            idempotency_key=idempotency_key if trigger.flow_type == FlowType.OBSERVE and not trigger.force else None,
            prompt_version=trigger.prompt_version or getattr(getattr(deps, 'settings', object()), 'prompt_version', 'prompt-v1'),
            agent_version=trigger.agent_version or getattr(getattr(deps, 'settings', object()), 'agent_version', 'agent-v1'),
            feature_set_version=trigger.feature_set_version or getattr(getattr(deps, 'settings', object()), 'feature_set_version', 'feature-set-v1'),
            model_version=trigger.model_version or getattr(getattr(deps, 'settings', object()), 'model_version', 'model-v1'),
            input_json=trigger.model_dump(mode='json'),
            output_json={},
            metadata_json={},
            error_json={},
        )
        workflow_run = WorkflowRunOut.model_validate(run)
        if async_mode and self._async_dispatcher and trigger.flow_type in {FlowType.OBSERVE, FlowType.REASON, FlowType.REVIEW}:
            self._async_dispatcher(run.run_id)
        elif not async_mode:
            self.execute_run(run.run_id)
            workflow_run = WorkflowRunOut.model_validate(deps.workflow_runs.get(run.run_id))
        return workflow_run

    def execute_run(self, run_id: str) -> WorkflowRunOut:
        deps = self._deps_factory()
        run = deps.workflow_runs.get(run_id)
        state_payload = run.output_json or run.input_json or {}
        state = FlowState(
            run_id=run.run_id,
            flow_type=run.flow_type,
            as_of_date=run.as_of_date,
            prompt_version=run.prompt_version,
            agent_version=run.agent_version,
            feature_set_version=run.feature_set_version,
            model_version=run.model_version,
            status=run.status,
            payload=state_payload.get('payload', run.input_json.get('payload', {})),
            metadata=state_payload.get('metadata', {}),
            watchlist_symbols=state_payload.get('watchlist_symbols', run.input_json.get('watchlist_symbols', [])),
            news_articles=state_payload.get('news_articles', []),
            historical_briefs=state_payload.get('historical_briefs', []),
            daily_brief=state_payload.get('daily_brief'),
            market_snapshots=state_payload.get('market_snapshots', {}),
            indicator_snapshots=state_payload.get('indicator_snapshots', {}),
            evidence_pack=[EvidenceRef.model_validate(item) for item in state_payload.get('evidence_pack', [])],
            candidates=[CandidateOut.model_validate(item) for item in state_payload.get('candidates', [])],
            agent_messages=state_payload.get('agent_messages', []),
            agent_results=state_payload.get('agent_results', {}),
            recommendations=[CandidateOut.model_validate(item) for item in state_payload.get('recommendations', [])],
            prediction_artifacts=state_payload.get('prediction_artifacts', []),
            trade_ocr=TradeOCRResult.model_validate(state_payload.get('trade_ocr')) if state_payload.get('trade_ocr') else None,
            user_confirmation=state_payload.get('user_confirmation', run.input_json.get('payload', {}).get('user_confirmation')),
            review_verdict=ReviewVerdict.model_validate(state_payload.get('review_verdict')) if state_payload.get('review_verdict') else None,
            knowledge_items=[KnowledgeItem.model_validate(item) for item in state_payload.get('knowledge_items', [])],
            errors=state_payload.get('errors', []),
        )
        runner = build_flow_runner(run.flow_type, deps)
        runner.run(state)
        return WorkflowRunOut.model_validate(deps.workflow_runs.get(run_id))

    def resume_act_run(self, run_id: str, confirmed: bool) -> WorkflowRunOut:
        deps = self._deps_factory()
        run = deps.workflow_runs.get(run_id)
        payload = dict(run.output_json or {})
        payload['user_confirmation'] = confirmed
        deps.workflow_runs.update(run_id, output_json=payload)
        return self.execute_run(run_id)

    def get_run(self, run_id: str) -> WorkflowRunOut | None:
        deps = self._deps_factory()
        run = deps.workflow_runs.get(run_id)
        return WorkflowRunOut.model_validate(run) if run else None

    def get_run_logs(self, run_id: str):
        deps = self._deps_factory()
        return deps.agent_node_runs.list_by_run(run_id)

    def get_run_recommendations(self, run_id: str) -> list[RecommendationRecordOut]:
        deps = self._deps_factory()
        rows = deps.recommendation_repository.list_by_run(run_id)
        return [RecommendationRecordOut.model_validate(row) for row in rows]

    def get_review_report(self, run_id: str) -> ReviewReportOut | None:
        deps = self._deps_factory()
        row = deps.review_repository.get_by_run(run_id)
        return ReviewReportOut.model_validate(row) if row else None

    def list_hot_knowledge(self, limit: int = 100) -> list[HotKnowledgeOut]:
        deps = self._deps_factory()
        rows = deps.knowledge_repository.list_hot(limit=limit)
        return [HotKnowledgeOut.model_validate(row) for row in rows]

    def get_active_cold_knowledge(
        self,
        category: str | None = None,
        market_regime: str | None = None,
        limit: int = 100,
    ) -> list[ColdKnowledge]:
        deps = self._deps_factory()
        rows = deps.knowledge_repository.get_active_cold_knowledge(
            category=category,
            market_regime=market_regime,
            limit=limit,
        )
        return [ColdKnowledge.model_validate(row) for row in rows]

    @staticmethod
    def _build_idempotency_key(trigger: WorkflowTriggerIn) -> str:
        if trigger.flow_type is None:
            raise ValueError('flow_type is required to build idempotency key')
        return f"{trigger.flow_type.value}:{trigger.as_of_date.isoformat()}"
