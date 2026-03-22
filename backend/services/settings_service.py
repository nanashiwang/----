from typing import Dict, List, Optional
from datetime import datetime
from src.data.db.sqlite_client import SQLiteClient


class SettingsService:
    def __init__(self, db: SQLiteClient):
        self.db = db

    def get_settings(self, category: str) -> List[Dict]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT key, value, is_secret FROM system_settings WHERE category = ?",
                (category,)
            ).fetchall()
            result = []
            for r in rows:
                val = r["value"]
                if r["is_secret"] and val:
                    val = val[:4] + "****" + val[-4:] if len(val) > 8 else "****"
                result.append({"key": r["key"], "value": val, "is_secret": bool(r["is_secret"])})
            return result

    def get_raw_value(self, category: str, key: str) -> Optional[str]:
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM system_settings WHERE category = ? AND key = ?",
                (category, key)
            ).fetchone()
            return row["value"] if row else None

    @staticmethod
    def _is_masked_secret(value: Optional[str]) -> bool:
        return isinstance(value, str) and "****" in value

    def update_settings(self, category: str, items: List[Dict], user_id: int = None):
        with self.db.get_connection() as conn:
            for item in items:
                value = item["value"]
                if item.get("is_secret") and self._is_masked_secret(value):
                    existing = conn.execute(
                        "SELECT value FROM system_settings WHERE category = ? AND key = ?",
                        (category, item["key"])
                    ).fetchone()
                    value = existing["value"] if existing else value

                conn.execute("""
                    INSERT INTO system_settings (category, key, value, is_secret, updated_by, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(category, key) DO UPDATE SET
                        value = excluded.value,
                        is_secret = excluded.is_secret,
                        updated_by = excluded.updated_by,
                        updated_at = excluded.updated_at
                """, (category, item["key"], value, item.get("is_secret", False),
                      user_id, datetime.now()))
            conn.commit()

    def seed_defaults(self):
        """从config.yaml/环境变量写入默认值（如果表为空）"""
        with self.db.get_connection() as conn:
            count = conn.execute("SELECT COUNT(*) as c FROM system_settings").fetchone()["c"]
            if count > 0:
                return

        from src.utils.config import get_config
        try:
            config = get_config()
            defaults = [
                ("llm", "provider", config.llm.provider, False),
                ("llm", "api_base", config.llm.api_base, False),
                ("llm", "api_key", config.llm.api_key, True),
                ("llm", "model", config.llm.model, False),
                ("llm", "temperature", str(config.llm.temperature), False),
                ("llm", "max_tokens", str(config.llm.max_tokens), False),
                ("tushare", "token", config.tushare.token, True),
            ]
            with self.db.get_connection() as conn:
                for cat, key, val, secret in defaults:
                    conn.execute("""
                        INSERT OR IGNORE INTO system_settings (category, key, value, is_secret)
                        VALUES (?, ?, ?, ?)
                    """, (cat, key, val, secret))
                conn.commit()
        except Exception:
            pass


class AgentConfigService:
    def __init__(self, db: SQLiteClient):
        self.db = db

    def list_all(self) -> List[Dict]:
        with self.db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM agent_configs ORDER BY cluster, id").fetchall()
            return [dict(r) for r in rows]

    def get_by_id(self, agent_id: int) -> Optional[Dict]:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM agent_configs WHERE id = ?", (agent_id,)).fetchone()
            return dict(row) if row else None

    def update(self, agent_id: int, data: Dict):
        if not data:
            raise ValueError("至少提供一个可更新字段")
        with self.db.get_connection() as conn:
            data["updated_at"] = datetime.now()
            sets = ", ".join(f"{k} = ?" for k in data)
            values = list(data.values()) + [agent_id]
            conn.execute(f"UPDATE agent_configs SET {sets} WHERE id = ?", values)
            conn.commit()

    def seed_defaults(self):
        """插入默认Agent配置"""
        with self.db.get_connection() as conn:
            count = conn.execute("SELECT COUNT(*) as c FROM agent_configs").fetchone()["c"]
            if count > 0:
                return
            defaults = [
                ("observe", "event_collector", "事件收集专员", "收集市场事件并生成简报"),
                ("observe", "tech_analyst", "技术指标专员", "分析股票技术指标"),
                ("reason", "news_screener", "消息面筛选", "基于事件简报初筛候选"),
                ("reason", "debate_defender", "辩护者", "挖掘利好因素"),
                ("reason", "debate_critic", "批评者", "挖掘风险点"),
                ("reason", "debate_arbiter", "仲裁者", "综合判断"),
                ("reason", "hat_white", "白帽-数据", "纯客观数据分析"),
                ("reason", "hat_red", "红帽-情绪", "市场情绪判断"),
                ("reason", "hat_black", "黑帽-风险", "风险评估"),
                ("reason", "hat_yellow", "黄帽-机会", "潜在收益分析"),
                ("reason", "hat_green", "绿帽-创新", "非常规角度"),
                ("reason", "hat_blue", "蓝帽-总结", "整合结论"),
                ("act", "trade_recorder", "交易记录员", "OCR识别交割单"),
                ("review", "retrospect_agent", "复盘分析师", "对比推荐与实际结果"),
            ]
            for cluster, name, display, prompt in defaults:
                conn.execute("""
                    INSERT INTO agent_configs (cluster, agent_name, display_name, system_prompt)
                    VALUES (?, ?, ?, ?)
                """, (cluster, name, display, prompt))
            conn.commit()
