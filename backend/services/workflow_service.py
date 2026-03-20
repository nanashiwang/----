import asyncio
import threading
from typing import Dict, Optional
from datetime import datetime


class WorkflowRunner:
    """工作流后台执行器"""

    _status: Dict[str, Dict] = {}
    _lock = threading.Lock()

    @classmethod
    def get_status(cls, workflow_id: str) -> Optional[Dict]:
        with cls._lock:
            return cls._status.get(workflow_id)

    @classmethod
    def _set_status(cls, workflow_id: str, status: str, message: str = ""):
        with cls._lock:
            cls._status[workflow_id] = {
                "status": status, "message": message,
                "updated_at": datetime.now().isoformat()
            }

    @classmethod
    def run_observe(cls, date: str):
        workflow_id = f"observe_{date}"
        cls._set_status(workflow_id, "running", "观察工作流启动中...")

        def _run():
            try:
                from backend.services.settings_service import SettingsService
                from backend.app import get_sqlite_client
                from src.llm.factory import LLMFactory
                from src.data.sources.tushare_api import TushareAPI
                from src.agents.observe.event_collector import EventCollector
                from src.agents.observe.tech_analyst import TechAnalyst
                from src.workflows.observe_flow import create_observe_workflow

                db = get_sqlite_client()
                svc = SettingsService(db)
                provider = svc.get_raw_value("llm", "provider") or "openai"
                api_key = svc.get_raw_value("llm", "api_key")
                api_base = svc.get_raw_value("llm", "api_base")
                model = svc.get_raw_value("llm", "model") or "gpt-4"
                token = svc.get_raw_value("tushare", "token")

                llm = LLMFactory.create(provider, api_key=api_key, api_base=api_base, model=model)
                ts_api = TushareAPI(token)

                cls._set_status(workflow_id, "running", "获取新闻数据...")
                news_df = ts_api.get_news(date.replace("-", ""), date.replace("-", ""))
                news_data = news_df.to_dict("records") if not news_df.empty else []

                stock_pool = ts_api.get_stock_basic()["ts_code"].tolist()[:10]

                cls._set_status(workflow_id, "running", "执行工作流...")
                ec = EventCollector(llm, db)
                ta = TechAnalyst(ts_api, db)
                workflow = create_observe_workflow(ec, ta)
                workflow.invoke({
                    "date": date, "news_data": news_data,
                    "stock_codes": stock_pool, "event_brief": "", "tech_data": {}
                })
                cls._set_status(workflow_id, "completed", "观察工作流完成")
            except Exception as e:
                cls._set_status(workflow_id, "failed", str(e))

        threading.Thread(target=_run, daemon=True).start()
        return workflow_id

    @classmethod
    def run_reason(cls, date: str):
        workflow_id = f"reason_{date}"
        cls._set_status(workflow_id, "running", "推理工作流启动中...")

        def _run():
            try:
                from backend.services.settings_service import SettingsService
                from backend.app import get_sqlite_client
                from src.llm.factory import LLMFactory
                from src.data.sources.tushare_api import TushareAPI
                from src.agents.reason.news_screener import NewsScreener
                from src.workflows.reason_flow import create_reason_workflow

                db = get_sqlite_client()
                svc = SettingsService(db)
                provider = svc.get_raw_value("llm", "provider") or "openai"
                api_key = svc.get_raw_value("llm", "api_key")
                api_base = svc.get_raw_value("llm", "api_base")
                model = svc.get_raw_value("llm", "model") or "gpt-4"
                token = svc.get_raw_value("tushare", "token")

                llm = LLMFactory.create(provider, api_key=api_key, api_base=api_base, model=model)
                ts_api = TushareAPI(token)

                with db.get_connection() as conn:
                    row = conn.execute("SELECT content FROM event_briefs WHERE date = ?", (date,)).fetchone()
                    event_brief = row["content"] if row else "无简报"

                stock_pool = ts_api.get_stock_basic()["ts_code"].tolist()[:100]
                screener = NewsScreener(llm)
                workflow = create_reason_workflow(screener, llm, db)
                workflow.invoke({
                    "event_brief": event_brief, "stock_pool": stock_pool,
                    "tech_data": {}, "candidates": [], "debate_results": {}, "final_picks": []
                })
                cls._set_status(workflow_id, "completed", "推理工作流完成")
            except Exception as e:
                cls._set_status(workflow_id, "failed", str(e))

        threading.Thread(target=_run, daemon=True).start()
        return workflow_id

    @classmethod
    def run_review(cls, date: str):
        workflow_id = f"review_{date}"
        cls._set_status(workflow_id, "running", "复盘工作流启动中...")

        def _run():
            try:
                from backend.services.settings_service import SettingsService
                from backend.app import get_sqlite_client, get_mongo_client
                from src.llm.factory import LLMFactory
                from src.data.sources.tushare_api import TushareAPI
                from src.agents.review.retrospect_agent import RetrospectAgent
                from src.workflows.review_flow import create_review_workflow

                db = get_sqlite_client()
                mongo = get_mongo_client()
                svc = SettingsService(db)
                provider = svc.get_raw_value("llm", "provider") or "openai"
                api_key = svc.get_raw_value("llm", "api_key")
                api_base = svc.get_raw_value("llm", "api_base")
                model = svc.get_raw_value("llm", "model") or "gpt-4"
                token = svc.get_raw_value("tushare", "token")

                llm = LLMFactory.create(provider, api_key=api_key, api_base=api_base, model=model)
                ts_api = TushareAPI(token)

                agent = RetrospectAgent(llm, db, mongo, ts_api)
                workflow = create_review_workflow(agent)
                workflow.invoke({"date": date, "review_result": {}})
                cls._set_status(workflow_id, "completed", "复盘工作流完成")
            except Exception as e:
                cls._set_status(workflow_id, "failed", str(e))

        threading.Thread(target=_run, daemon=True).start()
        return workflow_id
