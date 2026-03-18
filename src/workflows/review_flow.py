from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END
from ..agents.review.retrospect_agent import RetrospectAgent


class ReviewState(TypedDict):
    """复盘工作流状态"""
    date: str
    review_result: Dict[str, Any]


def create_review_workflow(retrospect_agent: RetrospectAgent):
    """创建复盘工作流"""

    def review_node(state: ReviewState) -> ReviewState:
        """复盘节点"""
        result = retrospect_agent.run(state["date"])
        state["review_result"] = result
        return state

    workflow = StateGraph(ReviewState)
    workflow.add_node("review", review_node)
    workflow.set_entry_point("review")
    workflow.add_edge("review", END)

    return workflow.compile()
