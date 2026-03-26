from typing import Dict, Any, List
from datetime import datetime, timedelta
from ...llm.base import BaseLLM
from ...data.db.sqlite_client import SQLiteClient
from ...data.db.mongo_client import MongoDBClient
from ...data.sources.tushare_api import TushareAPI


class RetrospectAgent:
    """复盘分析师"""

    def __init__(self, llm: BaseLLM, sqlite_client: SQLiteClient,
                 mongo_client: MongoDBClient, tushare_api: TushareAPI):
        self.llm = llm
        self.db = sqlite_client
        self.mongo = mongo_client
        self.ts = tushare_api

    def load_recommendations(self, date: str) -> List[Dict]:
        """加载推荐记录"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {self.db.LEGACY_RECOMMENDATIONS_TABLE} WHERE date = ?", (date,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_actual_performance(self, ts_code: str, date: str, days: int = 5) -> Dict:
        """获取实际表现"""
        start = datetime.strptime(date, "%Y-%m-%d")
        end = start + timedelta(days=days)

        df = self.ts.get_daily_data(
            ts_code,
            start.strftime("%Y%m%d"),
            end.strftime("%Y%m%d")
        )

        if df.empty:
            return {"error": "无数据"}

        df = df.sort_values('trade_date')
        start_price = df.iloc[0]['close']
        end_price = df.iloc[-1]['close']
        return_rate = (end_price - start_price) / start_price

        return {
            "start_price": float(start_price),
            "end_price": float(end_price),
            "return_rate": float(return_rate),
            "success": return_rate > 0
        }

    def analyze_result(self, recommendation: Dict, performance: Dict) -> str:
        """分析结果"""
        prompt = f"""复盘分析：

【推荐信息】
股票：{recommendation['ts_code']}
权重：{recommendation['weight']}
理由：{recommendation['reason']}

【实际表现】
收益率：{performance.get('return_rate', 0):.2%}
结果：{'成功' if performance.get('success') else '失败'}

请用六顶思考帽分析：
1. 白帽：客观数据对比
2. 红帽：市场情绪变化
3. 黑帽：失败原因（如果失败）
4. 黄帽：成功因素（如果成功）
5. 绿帽：改进建议
6. 蓝帽：核心经验总结

输出格式：
【分析】...
【经验】..."""

        return self.llm.chat([{"role": "user", "content": prompt}])

    def extract_lessons(self, analysis: str) -> str:
        """提取经验教训"""
        prompt = f"""从以下复盘分析中提取1-2条可复用的经验：

{analysis}

要求：
- 简洁明了，每条30字内
- 可操作、可验证
- 只输出经验，不要其他内容"""

        return self.llm.chat([{"role": "user", "content": prompt}])

    def run(self, date: str) -> Dict[str, Any]:
        """执行复盘"""
        recommendations = self.load_recommendations(date)

        correct = []
        wrong = []
        insights = []

        for rec in recommendations:
            perf = self.get_actual_performance(rec['ts_code'], date)
            analysis = self.analyze_result(rec, perf)
            lesson = self.extract_lessons(analysis)

            if perf.get('success'):
                correct.append(rec['ts_code'])
            else:
                wrong.append(rec['ts_code'])

            insights.append(lesson)

            # 添加到热知识库
            category = "消息面" if "事件" in rec['reason'] else "技术面"
            self.mongo.add_hot_knowledge(lesson, category)

        # 保存复盘简报
        summary = f"推荐{len(recommendations)}只，成功{len(correct)}只，失败{len(wrong)}只"
        self.mongo.save_review_brief(
            datetime.strptime(date, "%Y-%m-%d"),
            summary, correct, wrong, insights
        )

        return {
            "date": date,
            "total": len(recommendations),
            "correct": len(correct),
            "wrong": len(wrong),
            "insights": insights
        }
