from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence

from backend.models.admin_log import AdminUsageLogListOut, AdminUsageSummaryOut
from src.data.db.sqlite_client import SQLiteClient

MODULE_LABELS = {
    "ml": "机器学习实验",
    "backtest": "回测系统",
}

ACTION_LABELS = {
    "experiment_run": "运行实验",
    "portfolio_backtest": "标准信号回测",
    "review_backtest": "推荐复盘",
}

STATUS_LABELS = {
    "success": "成功",
    "failed": "失败",
}

METRIC_LABELS = {
    "avg_future_return": "平均未来收益",
    "positive_future_return_ratio": "正收益占比",
    "avg_prediction_score": "平均预测分",
    "annualized_excess_return": "年化超额收益",
    "cumulative_return": "累计收益",
    "win_rate": "胜率",
    "avg_return": "平均收益",
    "avg_trade_return": "平均单笔收益",
}


class UsageLogService:
    def __init__(self, db: SQLiteClient):
        self.db = db

    def record_ml_experiment(self, user: Dict[str, Any], payload: Any, result: Dict[str, Any]) -> None:
        payload_data = self._to_plain_dict(payload)
        params = self._to_plain_dict(result.get("params"))
        prediction_summary = self._to_plain_dict(result.get("prediction_summary"))
        sample_summary = self._to_plain_dict(result.get("sample_summary"))
        training_summary = self._to_plain_dict(result.get("training_summary"))
        tuning_summary = self._to_plain_dict(result.get("tuning_summary"))
        resolved_symbols = params.get("resolved_symbols") or payload_data.get("symbols") or []
        status = "failed" if result.get("error") else "success"

        primary_metric_name = ""
        primary_metric_value = None
        if prediction_summary.get("avg_future_return") is not None:
            primary_metric_name = "avg_future_return"
            primary_metric_value = self._to_float(prediction_summary.get("avg_future_return"))
        elif prediction_summary.get("avg_prediction_score") is not None:
            primary_metric_name = "avg_prediction_score"
            primary_metric_value = self._to_float(prediction_summary.get("avg_prediction_score"))

        secondary_metric_name = ""
        secondary_metric_value = None
        if prediction_summary.get("positive_future_return_ratio") is not None:
            secondary_metric_name = "positive_future_return_ratio"
            secondary_metric_value = self._to_float(prediction_summary.get("positive_future_return_ratio"))

        self._insert_log(
            {
                "user_id": user.get("uid"),
                "username": str(user.get("sub") or "unknown"),
                "user_role": str(user.get("role") or "user"),
                "module": "ml",
                "action": "experiment_run",
                "method": self._build_ml_method(payload_data),
                "status": status,
                "label_column": str(payload_data.get("label_column") or ""),
                "symbols_count": len(resolved_symbols),
                "date_range_start": str(payload_data.get("train_start_date") or ""),
                "date_range_end": str(payload_data.get("predict_end_date") or ""),
                "primary_metric_name": primary_metric_name,
                "primary_metric_value": primary_metric_value,
                "secondary_metric_name": secondary_metric_name,
                "secondary_metric_value": secondary_metric_value,
                "error_message": str(result.get("error") or ""),
                "parameters_json": self._dump_json(
                    {
                        "model_type": payload_data.get("model_type"),
                        "tuning_method": payload_data.get("tuning_method"),
                        "hold_days": payload_data.get("hold_days"),
                        "max_features": payload_data.get("max_features"),
                        "prediction_top_n": payload_data.get("prediction_top_n"),
                        "symbols": resolved_symbols,
                        "feature_columns": payload_data.get("feature_columns") or [],
                        "use_feature_selection": bool(payload_data.get("use_feature_selection")),
                    }
                ),
                "result_summary_json": self._dump_json(
                    {
                        "sample_summary": sample_summary,
                        "training_summary": {
                            "train_score": training_summary.get("train_score"),
                            "train_metrics": training_summary.get("train_metrics"),
                            "validation_metrics": training_summary.get("validation_metrics"),
                        },
                        "prediction_summary": prediction_summary,
                        "tuning_summary": {
                            "method": tuning_summary.get("method"),
                            "message": tuning_summary.get("message"),
                            "best_params": tuning_summary.get("best_params", {}),
                        },
                        "selected_features": result.get("selected_features") or [],
                    }
                ),
            }
        )

    def record_backtest_run(
        self,
        user: Dict[str, Any],
        *,
        mode: str,
        model_type: str,
        start_date: str,
        end_date: str,
        hold_days: int,
        top_n: int,
        train_window_days: int,
        max_features: int,
        symbols: Sequence[str],
        result: Dict[str, Any],
    ) -> None:
        status = "failed" if result.get("error") else "success"
        primary_metric_name = ""
        primary_metric_value = None
        secondary_metric_name = ""
        secondary_metric_value = None
        result_summary: Dict[str, Any] = {}

        if mode == "review":
            primary_metric_name = "avg_return"
            primary_metric_value = self._to_float(result.get("avg_return"))
            secondary_metric_name = "win_rate"
            secondary_metric_value = self._to_float(result.get("win_rate"))
            result_summary = {
                "total_trades": result.get("total_trades"),
                "win_rate": result.get("win_rate"),
                "avg_return": result.get("avg_return"),
                "max_return": result.get("max_return"),
            }
        else:
            if model_type == "compare":
                winning_experiment = self._get_compare_winner_result(result)
                winning_summary = self._to_plain_dict(winning_experiment.get("summary"))
                primary_metric_name = "annualized_excess_return"
                primary_metric_value = self._to_float(winning_summary.get("annualized_excess_return"))
                secondary_metric_name = "cumulative_return"
                secondary_metric_value = self._to_float(winning_summary.get("cumulative_return"))
                result_summary = {
                    "winner": result.get("comparison_summary", {}).get("winner"),
                    "metric": result.get("comparison_summary", {}).get("metric"),
                    "metric_label": result.get("comparison_summary", {}).get("metric_label"),
                    "deltas": result.get("comparison_summary", {}).get("deltas", {}),
                    "experiments": [
                        {
                            "model_type": item.get("model_type"),
                            "summary": item.get("summary", {}),
                        }
                        for item in (result.get("experiments") or [])
                    ],
                }
            else:
                summary = self._to_plain_dict(result.get("summary"))
                primary_metric_name = "annualized_excess_return"
                primary_metric_value = self._to_float(summary.get("annualized_excess_return"))
                secondary_metric_name = "win_rate"
                secondary_metric_value = self._to_float(summary.get("win_rate"))
                result_summary = {
                    "strategy_name": result.get("strategy_name"),
                    "summary": summary,
                    "training_summary": result.get("training_summary", {}),
                    "selected_features": result.get("selected_features", []),
                }

        self._insert_log(
            {
                "user_id": user.get("uid"),
                "username": str(user.get("sub") or "unknown"),
                "user_role": str(user.get("role") or "user"),
                "module": "backtest",
                "action": "review_backtest" if mode == "review" else "portfolio_backtest",
                "method": self._build_backtest_method(mode=mode, model_type=model_type, hold_days=hold_days),
                "status": status,
                "label_column": "",
                "symbols_count": len(symbols or []),
                "date_range_start": start_date,
                "date_range_end": end_date,
                "primary_metric_name": primary_metric_name,
                "primary_metric_value": primary_metric_value,
                "secondary_metric_name": secondary_metric_name,
                "secondary_metric_value": secondary_metric_value,
                "error_message": str(result.get("error") or ""),
                "parameters_json": self._dump_json(
                    {
                        "mode": mode,
                        "model_type": model_type,
                        "start_date": start_date,
                        "end_date": end_date,
                        "hold_days": hold_days,
                        "top_n": top_n,
                        "train_window_days": train_window_days,
                        "max_features": max_features,
                        "symbols": list(symbols or []),
                    }
                ),
                "result_summary_json": self._dump_json(result_summary),
            }
        )

    def list_logs(
        self,
        *,
        limit: int = 100,
        module: str = "",
        username: str = "",
        method: str = "",
        status: str = "",
    ) -> Dict[str, Any]:
        where_sql, values = self._build_filters(module=module, username=username, method=method, status=status)
        with self.db.get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM usage_logs
                {where_sql}
                ORDER BY datetime(created_at) DESC, id DESC
                LIMIT ?
                """,
                [*values, max(1, min(limit, 200))],
            ).fetchall()

        items = [self._serialize_row(dict(row)) for row in rows]
        summary = self._build_summary(where_sql, values)
        return AdminUsageLogListOut(items=items, summary=summary).model_dump()

    def _build_summary(self, where_sql: str, values: List[Any]) -> AdminUsageSummaryOut:
        with self.db.get_connection() as conn:
            total_row = conn.execute(
                f"""
                SELECT
                    COUNT(*) AS total_runs,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success_runs,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_runs,
                    COUNT(DISTINCT username) AS unique_users,
                    SUM(CASE WHEN primary_metric_value > 0 THEN 1 ELSE 0 END) AS positive_primary_runs,
                    AVG(primary_metric_value) AS average_primary_value,
                    MAX(created_at) AS latest_run_at
                FROM usage_logs
                {where_sql}
                """,
                values,
            ).fetchone()

            best_row = conn.execute(
                f"""
                SELECT *
                FROM usage_logs
                {where_sql}
                {'AND' if where_sql else 'WHERE'} status = 'success' AND primary_metric_value IS NOT NULL
                ORDER BY primary_metric_value DESC, datetime(created_at) DESC
                LIMIT 1
                """,
                values,
            ).fetchone()

            method_rows = conn.execute(
                f"""
                SELECT
                    method AS name,
                    module,
                    primary_metric_name AS metric_name,
                    COUNT(*) AS run_count,
                    AVG(primary_metric_value) AS avg_value,
                    MAX(primary_metric_value) AS best_value
                FROM usage_logs
                {where_sql}
                {'AND' if where_sql else 'WHERE'} status = 'success' AND primary_metric_value IS NOT NULL
                GROUP BY module, method, primary_metric_name
                ORDER BY avg_value DESC, run_count DESC, method ASC
                LIMIT 8
                """,
                values,
            ).fetchall()

            module_rows = conn.execute(
                f"""
                SELECT
                    module AS name,
                    module,
                    primary_metric_name AS metric_name,
                    COUNT(*) AS run_count,
                    AVG(primary_metric_value) AS avg_value,
                    MAX(primary_metric_value) AS best_value
                FROM usage_logs
                {where_sql}
                GROUP BY module, primary_metric_name
                ORDER BY run_count DESC, module ASC
                LIMIT 8
                """,
                values,
            ).fetchall()

        return AdminUsageSummaryOut(
            total_runs=int(total_row["total_runs"] or 0),
            success_runs=int(total_row["success_runs"] or 0),
            failed_runs=int(total_row["failed_runs"] or 0),
            unique_users=int(total_row["unique_users"] or 0),
            positive_primary_runs=int(total_row["positive_primary_runs"] or 0),
            latest_run_at=str(total_row["latest_run_at"] or ""),
            average_primary_value=self._to_float(total_row["average_primary_value"]),
            best_run=self._serialize_row(dict(best_row)) if best_row else {},
            method_rankings=[self._serialize_ranking(dict(row)) for row in method_rows],
            module_breakdown=[self._serialize_ranking(dict(row)) for row in module_rows],
        )

    def _build_filters(self, *, module: str, username: str, method: str, status: str) -> tuple[str, List[Any]]:
        clauses: List[str] = []
        values: List[Any] = []
        if module:
            clauses.append("module = ?")
            values.append(module.strip())
        if username:
            clauses.append("username LIKE ?")
            values.append(f"%{username.strip()}%")
        if method:
            clauses.append("method LIKE ?")
            values.append(f"%{method.strip()}%")
        if status:
            clauses.append("status = ?")
            values.append(status.strip())
        if not clauses:
            return "", values
        return f"WHERE {' AND '.join(clauses)}", values

    def _insert_log(self, payload: Dict[str, Any]) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO usage_logs (
                    user_id,
                    username,
                    user_role,
                    module,
                    action,
                    method,
                    status,
                    label_column,
                    symbols_count,
                    date_range_start,
                    date_range_end,
                    primary_metric_name,
                    primary_metric_value,
                    secondary_metric_name,
                    secondary_metric_value,
                    error_message,
                    parameters_json,
                    result_summary_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.get("user_id"),
                    payload.get("username"),
                    payload.get("user_role"),
                    payload.get("module"),
                    payload.get("action"),
                    payload.get("method"),
                    payload.get("status"),
                    payload.get("label_column"),
                    payload.get("symbols_count"),
                    payload.get("date_range_start"),
                    payload.get("date_range_end"),
                    payload.get("primary_metric_name"),
                    payload.get("primary_metric_value"),
                    payload.get("secondary_metric_name"),
                    payload.get("secondary_metric_value"),
                    payload.get("error_message"),
                    payload.get("parameters_json"),
                    payload.get("result_summary_json"),
                ),
            )
            conn.commit()

    def _serialize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": int(row["id"]),
            "user_id": row.get("user_id"),
            "username": str(row.get("username") or ""),
            "user_role": str(row.get("user_role") or "user"),
            "module": str(row.get("module") or ""),
            "module_label": MODULE_LABELS.get(str(row.get("module") or ""), str(row.get("module") or "")),
            "action": str(row.get("action") or ""),
            "action_label": ACTION_LABELS.get(str(row.get("action") or ""), str(row.get("action") or "")),
            "method": str(row.get("method") or ""),
            "status": str(row.get("status") or "success"),
            "status_label": STATUS_LABELS.get(str(row.get("status") or "success"), str(row.get("status") or "")),
            "label_column": str(row.get("label_column") or ""),
            "symbols_count": int(row.get("symbols_count") or 0),
            "date_range_start": str(row.get("date_range_start") or ""),
            "date_range_end": str(row.get("date_range_end") or ""),
            "primary_metric_name": str(row.get("primary_metric_name") or ""),
            "primary_metric_label": self._metric_label(row.get("primary_metric_name")),
            "primary_metric_value": self._to_float(row.get("primary_metric_value")),
            "secondary_metric_name": str(row.get("secondary_metric_name") or ""),
            "secondary_metric_label": self._metric_label(row.get("secondary_metric_name")),
            "secondary_metric_value": self._to_float(row.get("secondary_metric_value")),
            "error_message": str(row.get("error_message") or ""),
            "parameters": self._load_json(row.get("parameters_json")),
            "result_summary": self._load_json(row.get("result_summary_json")),
            "created_at": str(row.get("created_at") or ""),
        }

    def _serialize_ranking(self, row: Dict[str, Any]) -> Dict[str, Any]:
        module = str(row.get("module") or "")
        metric_name = str(row.get("metric_name") or "")
        return {
            "name": str(row.get("name") or ""),
            "module": module,
            "module_label": MODULE_LABELS.get(module, module),
            "metric_name": metric_name,
            "metric_label": self._metric_label(metric_name),
            "run_count": int(row.get("run_count") or 0),
            "avg_value": self._to_float(row.get("avg_value")),
            "best_value": self._to_float(row.get("best_value")),
        }

    def _build_ml_method(self, payload_data: Dict[str, Any]) -> str:
        model_type = str(payload_data.get("model_type") or "unknown")
        tuning_method = str(payload_data.get("tuning_method") or "none")
        if tuning_method == "none":
            return model_type
        return f"{model_type} / {tuning_method}"

    def _build_backtest_method(self, *, mode: str, model_type: str, hold_days: int) -> str:
        if mode == "review":
            return f"review / hold_{hold_days}d"
        return model_type or "portfolio"

    def _get_compare_winner_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        winner = str(result.get("comparison_summary", {}).get("winner") or "")
        for item in result.get("experiments") or []:
            if str(item.get("model_type") or "") == winner:
                return item
        return (result.get("experiments") or [{}])[0]

    def _to_plain_dict(self, value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return {}

    def _dump_json(self, value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=self._json_default)

    def _load_json(self, value: Any) -> Dict[str, Any]:
        if not value:
            return {}
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {"value": parsed}

    def _metric_label(self, metric_name: Any) -> str:
        name = str(metric_name or "")
        return METRIC_LABELS.get(name, name)

    def _to_float(self, value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _json_default(self, value: Any) -> Any:
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except TypeError:
                return str(value)
        return str(value)

