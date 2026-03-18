from typing import Dict, Any
from PIL import Image
from ...llm.base import BaseLLM
from ...data.db.sqlite_client import SQLiteClient


class TradeRecorder:
    """交易记录员 - OCR识别交割单"""

    def __init__(self, llm: BaseLLM, sqlite_client: SQLiteClient):
        self.llm = llm
        self.db = sqlite_client

    def parse_trade_image(self, image_path: str) -> Dict[str, Any]:
        """解析交割单图片"""
        prompt = """请识别这张交割单图片，提取以下信息：
- 股票代码
- 交易日期
- 买入/卖出
- 成交价格
- 成交数量

输出JSON格式：
{"ts_code": "600519.SH", "trade_date": "2024-03-19", "action": "buy", "price": 1580.5, "volume": 100}"""

        # 注：实际使用需要多模态LLM（GPT-4V/Claude）
        # 这里简化处理
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.chat(messages)

        import json
        try:
            return json.loads(response)
        except:
            return {"error": "解析失败"}

    def save_trade(self, trade_data: Dict):
        """保存交易记录"""
        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT INTO trades (ts_code, trade_date, action, price, volume)
                VALUES (?, ?, ?, ?, ?)
            """, (
                trade_data["ts_code"],
                trade_data["trade_date"],
                trade_data["action"],
                trade_data["price"],
                trade_data["volume"]
            ))
            conn.commit()

    def run(self, image_path: str) -> Dict[str, Any]:
        """执行交易记录"""
        trade_data = self.parse_trade_image(image_path)
        if "error" not in trade_data:
            self.save_trade(trade_data)
        return trade_data
