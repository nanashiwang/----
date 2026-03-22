import json
import re
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

import pandas as pd

from backend.services.settings_service import SettingsService
from src.data.db.sqlite_client import SQLiteClient
from src.data.sources.tushare_api import TushareAPI


SUPPORTED_DATA_TYPES = ("daily", "daily_basic", "moneyflow", "top_list")
DEFAULT_DATA_TYPES = ("daily", "daily_basic", "moneyflow")
SUPPORTED_SYNC_MODES = ("incremental", "backfill")
TS_CODE_PATTERN = re.compile(r"^\d{6}\.(SH|SZ|BJ)$")


def _parse_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(value, default: int, minimum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(parsed, minimum)


def _parse_csv(value: str) -> List[str]:
    if not value:
        return []
    normalized = str(value).replace("\n", ",").replace("，", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def _infer_exchange_suffix(symbol: str) -> str:
    if not symbol.isdigit() or len(symbol) != 6:
        return ""
    if symbol.startswith(("4", "8")):
        return ".BJ"
    if symbol.startswith(("5", "6", "9")):
        return ".SH"
    return ".SZ"


def _normalize_symbol(symbol: str) -> str:
    normalized = str(symbol or "").strip().upper()
    if not normalized:
        return ""
    if "." in normalized:
        return normalized

    suffix = _infer_exchange_suffix(normalized)
    return f"{normalized}{suffix}" if suffix else normalized


def _normalize_symbols(symbols: List[str]) -> List[str]:
    return [item for item in (_normalize_symbol(symbol) for symbol in symbols) if item]


def _validate_symbols(symbols: List[str]) -> None:
    invalid_symbols = [symbol for symbol in symbols if not TS_CODE_PATTERN.fullmatch(symbol)]
    if invalid_symbols:
        preview = "、".join(invalid_symbols[:5])
        if len(invalid_symbols) > 5:
            preview += " 等"
        raise ValueError(f"股票代码格式不正确: {preview}。请使用 6 位代码或 000001.SZ 这类完整 ts_code")


def _normalize_trade_date(value) -> str:
    if value in (None, ""):
        return ""

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")

    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text[:10]


def _parse_sync_date(value) -> Optional[datetime]:
    normalized = _normalize_trade_date(value)
    if not normalized:
        return None
    try:
        return datetime.strptime(normalized, "%Y-%m-%d")
    except ValueError:
        return None


def _clean_value(value):
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


def _normalize_sync_mode(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in SUPPORTED_SYNC_MODES:
        return normalized
    return "incremental"


class MarketDataService:
    def __init__(self, db: SQLiteClient):
        self.db = db
        self.settings = SettingsService(db)

    def get_sync_settings(self) -> Dict:
        raw_types = _parse_csv(self.settings.get_raw_value("market_data", "data_types") or "")
        data_types = [item for item in raw_types if item in SUPPORTED_DATA_TYPES]
        if not data_types:
            data_types = list(DEFAULT_DATA_TYPES)

        return {
            "symbols": _normalize_symbols(_parse_csv(self.settings.get_raw_value("market_data", "symbols") or "")),
            "data_types": data_types,
            "fetch_interval": _parse_int(
                self.settings.get_raw_value("market_data", "fetch_interval"),
                default=3600,
                minimum=60,
            ),
            "history_days": _parse_int(
                self.settings.get_raw_value("market_data", "history_days"),
                default=30,
                minimum=1,
            ),
            "start_date": _normalize_trade_date(self.settings.get_raw_value("market_data", "start_date") or ""),
            "end_date": _normalize_trade_date(self.settings.get_raw_value("market_data", "end_date") or ""),
            "auto_sync": _parse_bool(self.settings.get_raw_value("market_data", "auto_sync")),
        }

    def get_runtime_status(self) -> Dict:
        return {
            "last_sync_at": self.settings.get_raw_value("market_data_runtime", "last_sync_at") or "",
            "last_sync_status": self.settings.get_raw_value("market_data_runtime", "last_sync_status") or "",
            "last_sync_message": self.settings.get_raw_value("market_data_runtime", "last_sync_message") or "",
        }

    def sync_if_due(self) -> Dict:
        settings = self.get_sync_settings()
        if not settings["auto_sync"] or not settings["symbols"]:
            return {"success": False, "skipped": True, "message": "自动同步未启用或股票池为空"}

        last_sync_at = self.get_runtime_status()["last_sync_at"]
        if last_sync_at:
            try:
                last_sync_dt = datetime.fromisoformat(last_sync_at)
            except ValueError:
                last_sync_dt = None
            if last_sync_dt is not None:
                elapsed = datetime.now() - last_sync_dt
                if elapsed < timedelta(seconds=settings["fetch_interval"]):
                    return {"success": False, "skipped": True, "message": "未达到下一次同步间隔"}

        return self.sync_configured_data(trigger="scheduler", mode="incremental")

    def sync_configured_data(
        self,
        trigger: str = "manual",
        mode: str = "incremental",
        progress_callback: Optional[Callable[[Dict], None]] = None,
    ) -> Dict:
        settings = self.get_sync_settings()
        symbols = settings["symbols"]
        data_types = settings["data_types"]
        mode = _normalize_sync_mode(mode)
        if not symbols:
            raise ValueError("请先配置需要拉取的股票代码")
        _validate_symbols(symbols)
        if not data_types:
            raise ValueError("请先选择至少一种拉取信息")

        token = self.settings.get_raw_value("tushare", "token")
        if not token:
            raise ValueError("请先配置 Tushare Token")
        api_url = self.settings.get_raw_value("tushare", "api_url") or ""

        start_dt, end_dt = self._resolve_sync_window(settings, mode)
        end_date = end_dt.strftime("%Y%m%d")
        start_date = start_dt.strftime("%Y%m%d")

        api = TushareAPI(token, api_url=api_url)
        daily_rows = 0
        snapshot_rows = 0
        errors: List[str] = []
        tasks = self._build_sync_tasks(symbols, data_types, start_date, end_date)
        total_tasks = len(tasks)

        self._emit_progress(
            progress_callback,
            current=0,
            total=total_tasks,
            current_task="",
            message=f"开始执行{self._get_mode_label(mode)}，共 {total_tasks} 个任务",
            errors=errors,
        )

        for index, task in enumerate(tasks, start=1):
            task_label = self._describe_task(task)
            self._emit_progress(
                progress_callback,
                current=index - 1,
                total=total_tasks,
                current_task=task_label,
                message=f"正在拉取 {task_label}",
                errors=errors,
            )

            try:
                task_result = self._execute_sync_task(api, task, symbols)
                daily_rows += task_result["daily_rows"]
                snapshot_rows += task_result["snapshot_rows"]
            except Exception as exc:
                errors.append(f"{task_label}: {exc}")

            summary = f"已完成 {index}/{total_tasks} 个任务"
            if errors:
                summary += f"，失败 {len(errors)} 项"
            self._emit_progress(
                progress_callback,
                current=index,
                total=total_tasks,
                current_task=task_label,
                message=summary,
                errors=errors,
            )

        sync_status = self._resolve_final_status(total_tasks, errors)
        message = self._build_sync_summary(
            trigger=trigger,
            mode=mode,
            start_dt=start_dt,
            end_dt=end_dt,
            symbol_count=len(symbols),
            daily_rows=daily_rows,
            snapshot_rows=snapshot_rows,
            error_count=len(errors),
        )
        self._update_runtime(sync_status, message)
        return {
            "success": sync_status != "failed",
            "status": sync_status,
            "message": message,
            "mode": mode,
            "symbol_count": len(symbols),
            "symbols": symbols,
            "data_types": data_types,
            "daily_rows": daily_rows,
            "snapshot_rows": snapshot_rows,
            "range_start": start_dt.strftime("%Y-%m-%d"),
            "range_end": end_dt.strftime("%Y-%m-%d"),
            "errors": errors,
        }

    def get_overview(
        self,
        ts_code: str = "",
        start_date: str = "",
        end_date: str = "",
        limit: int = 120,
    ) -> Dict:
        settings = self.get_sync_settings()
        symbols = settings["symbols"]
        selected_symbol = ts_code or (symbols[0] if symbols else "")
        runtime = self.get_runtime_status()

        if not selected_symbol:
            return {
                "symbols": [],
                "ts_code": "",
                "data_types": settings["data_types"],
                "records": [],
                "price_series": [],
                "latest_summary": {},
                "sync_window": {
                    "start_date": settings["start_date"],
                    "end_date": settings["end_date"],
                    "history_days": settings["history_days"],
                },
                "runtime": runtime,
            }

        records = self.list_records(
            ts_code=selected_symbol,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        price_series = [
            {
                "trade_date": row["trade_date"],
                "close": row.get("close"),
                "volume": row.get("volume"),
            }
            for row in reversed(records)
            if row.get("close") is not None
        ]
        latest = records[0] if records else {}
        latest_summary = {
            "trade_date": latest.get("trade_date", ""),
            "close": latest.get("close"),
            "open": latest.get("open"),
            "high": latest.get("high"),
            "low": latest.get("low"),
            "volume": latest.get("volume"),
            "amount": latest.get("amount"),
            "turnover_rate": latest.get("turnover_rate"),
            "pe": latest.get("pe"),
            "pb": latest.get("pb"),
            "net_mf_amount": latest.get("net_mf_amount"),
        }
        return {
            "symbols": symbols,
            "ts_code": selected_symbol,
            "data_types": settings["data_types"],
            "records": records,
            "price_series": price_series,
            "latest_summary": latest_summary,
            "sync_window": {
                "start_date": settings["start_date"],
                "end_date": settings["end_date"],
                "history_days": settings["history_days"],
            },
            "runtime": runtime,
        }

    def list_records(
        self,
        ts_code: str,
        start_date: str = "",
        end_date: str = "",
        limit: int = 120,
    ) -> List[Dict]:
        limit = max(1, min(limit, 500))
        daily_rows = self._query_daily_rows(ts_code, start_date, end_date, limit)
        snapshot_rows = self._query_snapshot_rows(ts_code, start_date, end_date, limit * 4)

        merged: Dict[str, Dict] = {}
        for row in daily_rows:
            trade_date = row["trade_date"]
            merged[trade_date] = {
                "trade_date": trade_date,
                "ts_code": row["ts_code"],
                "open": row["open"],
                "close": row["close"],
                "high": row["high"],
                "low": row["low"],
                "volume": row["volume"],
                "amount": row["amount"],
            }

        for row in snapshot_rows:
            trade_date = row["trade_date"]
            entry = merged.setdefault(trade_date, {"trade_date": trade_date, "ts_code": row["ts_code"]})
            metrics = json.loads(row["metrics_json"] or "{}")
            self._merge_metrics(entry, row["dataset"], metrics)

        return sorted(merged.values(), key=lambda item: item["trade_date"], reverse=True)[:limit]

    def _query_daily_rows(self, ts_code: str, start_date: str, end_date: str, limit: int):
        sql = "SELECT * FROM stock_data WHERE ts_code = ?"
        values: List = [ts_code]
        if start_date:
            sql += " AND trade_date >= ?"
            values.append(start_date)
        if end_date:
            sql += " AND trade_date <= ?"
            values.append(end_date)
        sql += " ORDER BY trade_date DESC LIMIT ?"
        values.append(limit)
        with self.db.get_connection() as conn:
            return conn.execute(sql, values).fetchall()

    def _query_snapshot_rows(self, ts_code: str, start_date: str, end_date: str, limit: int):
        sql = "SELECT * FROM market_data_snapshots WHERE ts_code = ?"
        values: List = [ts_code]
        if start_date:
            sql += " AND trade_date >= ?"
            values.append(start_date)
        if end_date:
            sql += " AND trade_date <= ?"
            values.append(end_date)
        sql += " ORDER BY trade_date DESC LIMIT ?"
        values.append(limit)
        with self.db.get_connection() as conn:
            return conn.execute(sql, values).fetchall()

    def _resolve_sync_window(self, settings: Dict, mode: str) -> tuple[datetime, datetime]:
        mode = _normalize_sync_mode(mode)
        explicit_start = _parse_sync_date(settings.get("start_date"))
        explicit_end = _parse_sync_date(settings.get("end_date"))
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if mode == "backfill":
            if not explicit_start and not explicit_end:
                raise ValueError("请先选择历史补数的时间范围")
            end_dt = explicit_end or datetime.now()
            start_dt = explicit_start or (end_dt - timedelta(days=settings["history_days"]))
        else:
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=settings["history_days"])

        if start_dt > end_dt:
            raise ValueError("拉取时间范围不正确：开始日期不能晚于结束日期")
        if mode == "backfill" and (start_dt > today or end_dt > today):
            raise ValueError(f"历史补数时间范围不能晚于今天（{today.strftime('%Y-%m-%d')}）")
        return start_dt, end_dt

    def _build_sync_tasks(
        self,
        symbols: List[str],
        data_types: List[str],
        start_date: str,
        end_date: str,
    ) -> List[Dict]:
        tasks: List[Dict] = []

        if "top_list" in data_types:
            tasks.append(
                {
                    "dataset": "top_list",
                    "ts_code": "",
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )

        for ts_code in symbols:
            for dataset in data_types:
                if dataset == "top_list":
                    continue
                tasks.append(
                    {
                        "dataset": dataset,
                        "ts_code": ts_code,
                        "start_date": start_date,
                        "end_date": end_date,
                    }
                )
        return tasks

    def _execute_sync_task(self, api: TushareAPI, task: Dict, symbols: List[str]) -> Dict:
        dataset = task["dataset"]
        ts_code = task["ts_code"]
        start_date = task["start_date"]
        end_date = task["end_date"]

        if dataset == "daily":
            return {
                "daily_rows": self._store_daily_rows(api.get_daily_data(ts_code, start_date, end_date)),
                "snapshot_rows": 0,
            }

        if dataset == "daily_basic":
            return {
                "daily_rows": 0,
                "snapshot_rows": self._store_snapshot_rows(
                    api.get_daily_basic(ts_code, start_date, end_date),
                    "daily_basic",
                ),
            }

        if dataset == "moneyflow":
            return {
                "daily_rows": 0,
                "snapshot_rows": self._store_snapshot_rows(
                    api.get_moneyflow(ts_code, start_date, end_date),
                    "moneyflow",
                ),
            }

        if dataset == "top_list":
            top_df = api.get_top_list(end_date)
            if symbols and not top_df.empty and "ts_code" in top_df.columns:
                top_df = top_df[top_df["ts_code"].isin(symbols)]
            return {
                "daily_rows": 0,
                "snapshot_rows": self._store_snapshot_rows(top_df, "top_list"),
            }

        raise ValueError(f"不支持的数据类型: {dataset}")

    def _describe_task(self, task: Dict) -> str:
        dataset_labels = {
            "daily": "日线行情",
            "daily_basic": "基础指标",
            "moneyflow": "资金流向",
            "top_list": "龙虎榜",
        }
        dataset = task["dataset"]
        dataset_label = dataset_labels.get(dataset, dataset)
        if dataset == "top_list":
            return dataset_label
        return f"{task['ts_code']} {dataset_label}"

    def _get_mode_label(self, mode: str) -> str:
        return "历史补数" if _normalize_sync_mode(mode) == "backfill" else "日常增量"

    def _resolve_final_status(self, total_tasks: int, errors: List[str]) -> str:
        if not errors:
            return "success"
        if len(errors) >= total_tasks:
            return "failed"
        return "partial"

    def _build_sync_summary(
        self,
        trigger: str,
        mode: str,
        start_dt: datetime,
        end_dt: datetime,
        symbol_count: int,
        daily_rows: int,
        snapshot_rows: int,
        error_count: int,
    ) -> str:
        summary = (
            f"{trigger} {self._get_mode_label(mode)}完成，区间 {start_dt.strftime('%Y-%m-%d')} ~ "
            f"{end_dt.strftime('%Y-%m-%d')}，股票 {symbol_count} 只，日线 {daily_rows} 行，"
            f"扩展指标 {snapshot_rows} 行"
        )
        if error_count:
            summary += f"，失败 {error_count} 项"
        return summary

    def _emit_progress(
        self,
        progress_callback: Optional[Callable[[Dict], None]],
        *,
        current: int,
        total: int,
        current_task: str,
        message: str,
        errors: List[str],
    ):
        if progress_callback is None:
            return

        progress = 0
        if total > 0:
            progress = int((current / total) * 100)

        progress_callback(
            {
                "current": current,
                "total": total,
                "progress": progress,
                "current_task": current_task,
                "message": message,
                "errors": list(errors),
            }
        )

    def _store_daily_rows(self, frame: Optional[pd.DataFrame]) -> int:
        if frame is None or frame.empty:
            return 0

        rows = 0
        with self.db.get_connection() as conn:
            for record in frame.to_dict("records"):
                conn.execute(
                    """
                    INSERT INTO stock_data (ts_code, trade_date, open, close, high, low, volume, amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(ts_code, trade_date) DO UPDATE SET
                        open = excluded.open,
                        close = excluded.close,
                        high = excluded.high,
                        low = excluded.low,
                        volume = excluded.volume,
                        amount = excluded.amount
                    """,
                    (
                        record.get("ts_code"),
                        _normalize_trade_date(record.get("trade_date")),
                        _clean_value(record.get("open")),
                        _clean_value(record.get("close")),
                        _clean_value(record.get("high")),
                        _clean_value(record.get("low")),
                        _clean_value(record.get("vol") or record.get("volume")),
                        _clean_value(record.get("amount")),
                    ),
                )
                rows += 1
            conn.commit()
        return rows

    def _store_snapshot_rows(self, frame: Optional[pd.DataFrame], dataset: str) -> int:
        if frame is None or frame.empty:
            return 0

        rows = 0
        with self.db.get_connection() as conn:
            for record in frame.to_dict("records"):
                ts_code = record.get("ts_code")
                trade_date = _normalize_trade_date(record.get("trade_date"))
                if not ts_code or not trade_date:
                    continue

                metrics = {
                    key: _clean_value(value)
                    for key, value in record.items()
                    if key not in {"ts_code", "trade_date"}
                }
                conn.execute(
                    """
                    INSERT INTO market_data_snapshots (ts_code, trade_date, dataset, metrics_json, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(ts_code, trade_date, dataset) DO UPDATE SET
                        metrics_json = excluded.metrics_json,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        ts_code,
                        trade_date,
                        dataset,
                        json.dumps(metrics, ensure_ascii=False),
                    ),
                )
                rows += 1
            conn.commit()
        return rows

    def _merge_metrics(self, target: Dict, dataset: str, metrics: Dict):
        if dataset == "daily_basic":
            for key in ("turnover_rate", "volume_ratio", "pe", "pb"):
                if key in metrics:
                    target[key] = metrics[key]
            return

        if dataset == "moneyflow":
            for key in (
                "buy_lg_amount",
                "sell_lg_amount",
                "buy_elg_amount",
                "sell_elg_amount",
                "net_mf_amount",
                "net_mf_vol",
            ):
                if key in metrics:
                    target[key] = metrics[key]
            return

        if dataset == "top_list":
            if "reason" in metrics:
                target["top_reason"] = metrics["reason"]
            if "net_amount" in metrics:
                target["top_net_amount"] = metrics["net_amount"]

    def _update_runtime(self, status: str, message: str):
        timestamp = datetime.now().isoformat(timespec="seconds")
        self.settings.update_settings(
            "market_data_runtime",
            [
                {"key": "last_sync_at", "value": timestamp, "is_secret": False},
                {"key": "last_sync_status", "value": status, "is_secret": False},
                {"key": "last_sync_message", "value": message, "is_secret": False},
            ],
        )
