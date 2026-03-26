from __future__ import annotations

from typing import Callable

from core.enums import RunStatus
from core.ids import generate_prefixed_id
from core.time import utcnow
from domain.schemas import FlowState


class BaseFlowRunner:
    flow_name = 'base'
    node_sequence: tuple[str, ...] = tuple()

    def __init__(self, deps):
        self.deps = deps

    def run(self, state: FlowState) -> FlowState:
        self.deps.workflow_runs.update(
            state.run_id,
            status=RunStatus.RUNNING,
            started_at=utcnow(),
        )
        for node_name in self.node_sequence:
            if state.status == RunStatus.WAITING_FOR_USER and state.user_confirmation is not True:
                break
            state = self._execute_node(node_name, getattr(self, node_name), state)
            self._snapshot_state(state)
            if state.status in {RunStatus.FAILED, RunStatus.WAITING_FOR_USER}:
                break

        if state.status in {RunStatus.RUNNING, RunStatus.PENDING}:
            state.status = RunStatus.COMPLETED

        finished_at = utcnow() if state.status in {RunStatus.COMPLETED, RunStatus.FAILED} else None
        self.deps.workflow_runs.update(
            state.run_id,
            status=state.status,
            finished_at=finished_at,
            output_json=state.model_dump(mode='json'),
            error_json={'errors': state.errors} if state.errors else {},
        )
        return state

    def _execute_node(self, node_name: str, node: Callable[[FlowState], FlowState], state: FlowState) -> FlowState:
        node_run = self.deps.agent_node_runs.start(
            node_run_id=generate_prefixed_id('node'),
            run_id=state.run_id,
            flow_type=state.flow_type,
            node_name=node_name,
            agent_name=node_name,
            status='running',
            input_json=state.model_dump(mode='json'),
            output_json={},
            evidence_refs_json={},
            error_json={},
            started_at=utcnow(),
        )
        try:
            state.current_node = node_name
            state.status = RunStatus.RUNNING
            updated_state = node(state)
            self.deps.agent_node_runs.finish(
                node_run.node_run_id,
                status=updated_state.status.value if hasattr(updated_state.status, 'value') else str(updated_state.status),
                output_json=updated_state.model_dump(mode='json'),
                evidence_refs_json={'items': [item.model_dump(mode='json') for item in updated_state.evidence_pack]},
                finished_at=utcnow(),
            )
            return updated_state
        except Exception as exc:
            error_json = {'type': exc.__class__.__name__, 'message': str(exc), 'node_name': node_name}
            state.errors.append(error_json)
            state.status = RunStatus.FAILED
            self.deps.agent_node_runs.fail(node_run.node_run_id, error_json=error_json, finished_at=utcnow())
            return state

    def _snapshot_state(self, state: FlowState) -> None:
        self.deps.workflow_runs.update(state.run_id, output_json=state.model_dump(mode='json'))
