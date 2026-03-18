from typing import Dict, Any, List
from datetime import datetime, timedelta
from ...llm.base import BaseLLM
from ...data.db.sqlite_client import SQLiteClient


class EventCollector:
    """事件收集专员 - 收集市场事件并生成简报"""

    def __init__(self, llm: BaseLLM, sqlite_client: SQLiteClient):
        self.llm = llm
        self.db = sqlite_client

    def collect_recent_briefs(self, days: int = 30) -> List[str]:
        """获取近期简报"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            cursor.execute(
                "SELECT date, content FROM event_briefs WHERE date >= ? ORDER BY date DESC",
                (start_date,)
            )
            return [f"{row['date']}: {row['content']}" for row in cursor.fetchall()]

    def generate_daily_brief(self, date: str, news_data: List[Dict]) -> str:
        """生成当日简报"""
        recent_briefs = self.collect_recent_briefs(30)
        recent_context = "\n".join(recent_briefs[:10]) if recent_briefs else "无历史简报"

        news_text = "\n".join([f"- {item.get('title', '')}: {item.get('content', '')[:100]}"
                               for item in news_data[:20]])

        prompt = f"""你是一位资深的市场分析师，负责生成每日市场事件简报。

## 近期简报参考
{recent_context}

## 今日新闻热点 ({date})
{news_text}

请生成今日市场事件简报，要求：
1. 提炼3-5个核心事件
2. 分析事件对市场的潜在影响
3. 标注相关板块和概念
4. 简洁明了，200字以内

输出格式：
【核心事件】
1. ...
2. ...

【市场影响】
...

【相关板块】
..."""

        messages = [
            {"role": "system", "content": "你是专业的市场分析师"},
            {"role": "user", "content": prompt}
        ]

        return self.llm.chat(messages)

    def save_brief(self, date: str, content: str, source: str = "auto"):
        """保存简报到数据库"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO event_briefs (date, content, source) VALUES (?, ?, ?)",
                (date, content, source)
            )
            conn.commit()

    def run(self, date: str, news_data: List[Dict]) -> Dict[str, Any]:
        """执行事件收集"""
        brief = self.generate_daily_brief(date, news_data)
        self.save_brief(date, brief)
        return {"date": date, "brief": brief}
