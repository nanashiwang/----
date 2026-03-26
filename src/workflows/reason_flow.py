from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from ..agents.reason.news_screener import NewsScreener, DebateAgent
from ..agents.reason.thinking_hats import ThinkingHatsTeam
from ..data.db.sqlite_client import SQLiteClient


class ReasonState(TypedDict):
    """推理工作流状态"""
    event_brief: str
    stock_pool: List[str]
    tech_data: Dict[str, Any]
    candidates: List[str]
    debate_results: Dict[str, Any]
    final_picks: List[Dict[str, Any]]


def create_reason_workflow(screener: NewsScreener, llm, sqlite_client: SQLiteClient):
    """创建推理工作流"""

    def screen_node(state: ReasonState) -> ReasonState:
        """初筛节点"""
        candidates = screener.screen_candidates(state["event_brief"], state["stock_pool"])
        state["candidates"] = candidates
        return state

    def debate_node(state: ReasonState) -> ReasonState:
        """辩论节点"""
        defender = DebateAgent(llm, "defender")
        critic = DebateAgent(llm, "critic")
        arbiter = DebateAgent(llm, "arbiter")

        results = {}
        for code in state["candidates"][:5]:  # 限制5只
            tech = state["tech_data"].get(code, {})
            defend_view = defender.analyze(code, state["event_brief"], tech)
            critic_view = critic.analyze(code, state["event_brief"], tech)
            decision = arbiter._arbitrate(code, defend_view, critic_view)
            results[code] = decision

        state["debate_results"] = results
        return state

    def thinking_hats_node(state: ReasonState) -> ReasonState:
        """思考帽节点"""
        team = ThinkingHatsTeam(llm)
        final_picks = []

        for code, debate in state["debate_results"].items():
            if debate.get("recommend", False):
                tech = state["tech_data"].get(code, {})
                result = team.analyze_stock(code, state["event_brief"], tech)
                final_picks.append(result)

        state["final_picks"] = sorted(final_picks, key=lambda x: x.get("weight", 0), reverse=True)
        return state

    def save_node(state: ReasonState) -> ReasonState:
        """保存结果节点"""
        from datetime import datetime
        import json

        with sqlite_client.get_connection() as conn:
            for pick in state["final_picks"]:
                conn.execute(f"""
                    INSERT INTO {sqlite_client.LEGACY_RECOMMENDATIONS_TABLE} (date, ts_code, weight, reason, agents_vote)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    datetime.now().strftime("%Y-%m-%d"),
                    pick["ts_code"],
                    pick.get("weight", 0),
                    pick.get("reason", ""),
                    json.dumps(pick.get("analysis", {}), ensure_ascii=False)
                ))
            conn.commit()
        return state

    workflow = StateGraph(ReasonState)
    workflow.add_node("screen", screen_node)
    workflow.add_node("debate", debate_node)
    workflow.add_node("thinking_hats", thinking_hats_node)
    workflow.add_node("save", save_node)

    workflow.set_entry_point("screen")
    workflow.add_edge("screen", "debate")
    workflow.add_edge("debate", "thinking_hats")
    workflow.add_edge("thinking_hats", "save")
    workflow.add_edge("save", END)

    return workflow.compile()
