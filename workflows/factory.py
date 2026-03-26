from __future__ import annotations

from core.enums import FlowType
from workflows.act_flow import ActFlowRunner
from workflows.observe_flow import ObserveFlowRunner
from workflows.reason_flow import ReasonFlowRunner
from workflows.review_flow import ReviewFlowRunner


def build_flow_runner(flow_type: FlowType, deps):
    mapping = {
        FlowType.OBSERVE: ObserveFlowRunner,
        FlowType.REASON: ReasonFlowRunner,
        FlowType.ACT: ActFlowRunner,
        FlowType.REVIEW: ReviewFlowRunner,
    }
    return mapping[flow_type](deps)
