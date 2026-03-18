from typing import Dict, Any, List
from ...llm.base import BaseLLM


class ThinkingHat:
    """思考帽Agent"""

    def __init__(self, llm: BaseLLM, color: str):
        self.llm = llm
        self.color = color

    def analyze(self, ts_code: str, context: Dict) -> str:
        """分析股票"""
        prompts = {
            "white": f"""【白帽-数据】纯客观分析 {ts_code}
技术数据：收盘{context['tech'].get('close')}，MA5={context['tech'].get('ma5')}，MACD={context['tech'].get('macd')}
只陈述事实和数据，不加主观判断。""",

            "red": f"""【红帽-情绪】分析 {ts_code} 的市场情绪
事件：{context.get('event_brief', '')[:100]}
从市场情绪、投资者心理角度分析，50字内。""",

            "black": f"""【黑帽-风险】评估 {ts_code} 的风险
技术+消息面综合考虑，列出3个主要风险点。""",

            "yellow": f"""【黄帽-机会】发掘 {ts_code} 的潜在收益
从积极角度分析上涨空间和催化剂。""",

            "green": f"""【绿帽-创新】非常规角度看 {ts_code}
跳出传统分析框架，提供新颖视角。""",

            "blue": f"""【蓝帽-总结】整合所有分析
白帽：{context.get('white', '')}
红帽：{context.get('red', '')}
黑帽：{context.get('black', '')}
黄帽：{context.get('yellow', '')}
绿帽：{context.get('green', '')}

给出最终结论：推荐权重(0-1)和核心理由。
输出JSON：{{"weight": 0.8, "reason": "..."}}"""
        }

        prompt = prompts.get(self.color, "")
        response = self.llm.chat([{"role": "user", "content": prompt}])

        if self.color == "blue":
            import json
            try:
                return json.loads(response)
            except:
                return {"weight": 0.5, "reason": "解析失败"}

        return response


class ThinkingHatsTeam:
    """六顶思考帽团队"""

    def __init__(self, llm: BaseLLM):
        self.hats = {
            color: ThinkingHat(llm, color)
            for color in ["white", "red", "black", "yellow", "green", "blue"]
        }

    def analyze_stock(self, ts_code: str, event_brief: str, tech_data: Dict) -> Dict:
        """完整分析流程"""
        context = {"tech": tech_data, "event_brief": event_brief}

        # 顺序执行5顶帽子
        for color in ["white", "red", "black", "yellow", "green"]:
            context[color] = self.hats[color].analyze(ts_code, context)

        # 蓝帽总结
        result = self.hats["blue"].analyze(ts_code, context)
        result["ts_code"] = ts_code
        result["analysis"] = context
        return result
