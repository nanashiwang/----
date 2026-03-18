from typing import Dict, Any, List
from ...llm.base import BaseLLM


class NewsScreener:
    """消息面筛选 - 基于事件简报初筛股票"""

    def __init__(self, llm: BaseLLM):
        self.llm = llm

    def screen_candidates(self, event_brief: str, stock_pool: List[str]) -> List[str]:
        """根据事件简报筛选候选股票"""
        prompt = f"""你是资深的消息面分析师。根据今日市场事件简报，从股票池中筛选出最有潜力的候选股票。

## 今日简报
{event_brief}

## 股票池
{', '.join(stock_pool[:50])}

请筛选出5-10只最相关的候选股票代码，要求：
1. 与事件高度相关
2. 有明确的逻辑支撑
3. 只输出股票代码，用逗号分隔

输出格式：600519.SH,000858.SZ,300750.SZ"""

        messages = [
            {"role": "system", "content": "你是专业的消息面分析师"},
            {"role": "user", "content": prompt}
        ]

        response = self.llm.chat(messages)
        candidates = [code.strip() for code in response.split(',') if code.strip()]
        return candidates[:10]


class DebateAgent:
    """辩论Agent - 辩护者、批评者、仲裁者"""

    def __init__(self, llm: BaseLLM, role: str):
        self.llm = llm
        self.role = role  # defender/critic/arbiter

    def analyze(self, ts_code: str, event_brief: str, tech_data: Dict) -> str:
        """分析股票"""
        if self.role == "defender":
            return self._defend(ts_code, event_brief, tech_data)
        elif self.role == "critic":
            return self._criticize(ts_code, event_brief, tech_data)
        else:
            return self._arbitrate(ts_code, event_brief, tech_data)

    def _defend(self, ts_code: str, event_brief: str, tech_data: Dict) -> str:
        """辩护者 - 挖掘利好"""
        prompt = f"""你是看多的辩护者，请为股票 {ts_code} 找出所有利好因素。

事件简报：{event_brief}

技术数据：
- 收盘价：{tech_data.get('close')}
- MA5：{tech_data.get('ma5')}
- MACD：{tech_data.get('macd')}

请列出3-5个看多理由，每个理由要有具体依据。"""

        return self.llm.chat([{"role": "user", "content": prompt}])

    def _criticize(self, ts_code: str, event_brief: str, tech_data: Dict) -> str:
        """批评者 - 挖掘风险"""
        prompt = f"""你是看空的批评者，请为股票 {ts_code} 找出所有风险点。

事件简报：{event_brief}

技术数据：
- 收盘价：{tech_data.get('close')}
- MA5：{tech_data.get('ma5')}
- MACD：{tech_data.get('macd')}

请列出3-5个风险点，每个风险要有具体依据。"""

        return self.llm.chat([{"role": "user", "content": prompt}])

    def _arbitrate(self, ts_code: str, defender_view: str, critic_view: str) -> Dict:
        """仲裁者 - 综合判断"""
        prompt = f"""你是中立的仲裁者，综合多空双方观点，给出最终判断。

股票：{ts_code}

【多方观点】
{defender_view}

【空方观点】
{critic_view}

请给出：
1. 综合评分（0-100）
2. 是否推荐（是/否）
3. 核心理由（50字内）

输出JSON格式：{{"score": 75, "recommend": true, "reason": "..."}}"""

        response = self.llm.chat([{"role": "user", "content": prompt}])
        import json
        try:
            return json.loads(response)
        except:
            return {"score": 50, "recommend": False, "reason": "解析失败"}
