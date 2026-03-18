from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from ..agents.observe.event_collector import EventCollector
from ..agents.observe.tech_analyst import TechAnalyst


class ObserveState(TypedDict):
    """观察工作流状态"""
    date: str
    news_data: List[Dict]
    stock_codes: List[str]
    event_brief: str
    tech_data: Dict[str, Any]


def create_observe_workflow(event_collector: EventCollector, tech_analyst: TechAnalyst):
    """创建观察工作流"""

    def collect_events_node(state: ObserveState) -> ObserveState:
        """事件收集节点"""
        result = event_collector.run(state["date"], state["news_data"])
        state["event_brief"] = result["brief"]
        return state

    def analyze_tech_node(state: ObserveState) -> ObserveState:
        """技术分析节点"""
        result = tech_analyst.run(state["stock_codes"])
        state["tech_data"] = result["tech_data"]
        return state

    workflow = StateGraph(ObserveState)
    workflow.add_node("collect_events", collect_events_node)
    workflow.add_node("analyze_tech", analyze_tech_node)

    workflow.set_entry_point("collect_events")
    workflow.add_edge("collect_events", "analyze_tech")
    workflow.add_edge("analyze_tech", END)

    return workflow.compile()
