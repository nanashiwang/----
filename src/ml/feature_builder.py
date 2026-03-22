import json
from typing import Iterable, List, Optional

import pandas as pd

from ..data.db.sqlite_client import SQLiteClient


class FeatureBuilder:
    """从 SQLite 行情表构建可训练的特征面板。"""

    def __init__(self, sqlite_client: SQLiteClient):
        self.db = sqlite_client

    def load_market_frame(
        self,
        symbols: Optional[Iterable[str]] = None,
        start_date: str = "",
        end_date: str = "",
    ) -> pd.DataFrame:
        daily_df = self._load_daily_frame(symbols=symbols, start_date=start_date, end_date=end_date)
        if daily_df.empty:
            return daily_df

        snapshot_df = self._load_snapshot_frame(symbols=symbols, start_date=start_date, end_date=end_date)
        merged = self._merge_snapshot_metrics(daily_df, snapshot_df)
        return self._build_features(merged)

    def _load_daily_frame(
        self,
        symbols: Optional[Iterable[str]] = None,
        start_date: str = "",
        end_date: str = "",
    ) -> pd.DataFrame:
        sql = """
            SELECT ts_code, trade_date, open, close, high, low, volume, amount
            FROM stock_data
            WHERE 1 = 1
        """
        params: List[str] = []
        symbol_list = [item for item in (symbols or []) if item]
        if symbol_list:
            placeholders = ",".join("?" for _ in symbol_list)
            sql += f" AND ts_code IN ({placeholders})"
            params.extend(symbol_list)
        if start_date:
            sql += " AND trade_date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND trade_date <= ?"
            params.append(end_date)
        sql += " ORDER BY ts_code, trade_date"

        with self.db.get_connection() as conn:
            frame = pd.read_sql_query(sql, conn, params=params)

        if frame.empty:
            return frame

        frame["trade_date"] = pd.to_datetime(frame["trade_date"])
        for column in ("open", "close", "high", "low", "volume", "amount"):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return frame

    def _load_snapshot_frame(
        self,
        symbols: Optional[Iterable[str]] = None,
        start_date: str = "",
        end_date: str = "",
    ) -> pd.DataFrame:
        sql = """
            SELECT ts_code, trade_date, dataset, metrics_json
            FROM market_data_snapshots
            WHERE 1 = 1
        """
        params: List[str] = []
        symbol_list = [item for item in (symbols or []) if item]
        if symbol_list:
            placeholders = ",".join("?" for _ in symbol_list)
            sql += f" AND ts_code IN ({placeholders})"
            params.extend(symbol_list)
        if start_date:
            sql += " AND trade_date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND trade_date <= ?"
            params.append(end_date)
        sql += " ORDER BY ts_code, trade_date, dataset"

        with self.db.get_connection() as conn:
            frame = pd.read_sql_query(sql, conn, params=params)

        if frame.empty:
            return frame

        frame["trade_date"] = pd.to_datetime(frame["trade_date"])
        return frame

    def _merge_snapshot_metrics(self, daily_df: pd.DataFrame, snapshot_df: pd.DataFrame) -> pd.DataFrame:
        merged = daily_df.copy()
        if snapshot_df.empty:
            merged["top_list_flag"] = 0.0
            return merged

        expanded = []
        for row in snapshot_df.to_dict("records"):
            metrics = json.loads(row.get("metrics_json") or "{}")
            expanded.append(
                {
                    "ts_code": row["ts_code"],
                    "trade_date": row["trade_date"],
                    "dataset": row["dataset"],
                    **metrics,
                }
            )

        snapshot_records = pd.DataFrame(expanded)
        if snapshot_records.empty:
            merged["top_list_flag"] = 0.0
            return merged

        for dataset in snapshot_records["dataset"].dropna().unique().tolist():
            dataset_frame = snapshot_records[snapshot_records["dataset"] == dataset].drop(columns=["dataset"]).copy()
            if dataset == "top_list":
                dataset_frame["top_list_flag"] = 1.0
                if "net_amount" in dataset_frame.columns and "top_net_amount" not in dataset_frame.columns:
                    dataset_frame = dataset_frame.rename(columns={"net_amount": "top_net_amount"})
                if "reason" in dataset_frame.columns and "top_reason" not in dataset_frame.columns:
                    dataset_frame = dataset_frame.rename(columns={"reason": "top_reason"})
            dataset_frame = dataset_frame.drop_duplicates(subset=["ts_code", "trade_date"], keep="last")
            merged = merged.merge(dataset_frame, on=["ts_code", "trade_date"], how="left")

        numeric_columns = [
            "turnover_rate",
            "volume_ratio",
            "pe",
            "pb",
            "buy_lg_amount",
            "sell_lg_amount",
            "buy_elg_amount",
            "sell_elg_amount",
            "net_mf_amount",
            "net_mf_vol",
            "top_net_amount",
        ]
        for column in numeric_columns:
            if column in merged.columns:
                merged[column] = pd.to_numeric(merged[column], errors="coerce")

        if "top_list_flag" not in merged.columns:
            merged["top_list_flag"] = 0.0
        merged["top_list_flag"] = merged["top_list_flag"].fillna(0.0)
        return merged

    def _build_features(self, frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return frame

        frame = frame.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)
        by_symbol = frame.groupby("ts_code", group_keys=False)

        frame["return_1d"] = by_symbol["close"].transform(lambda series: series.pct_change())
        frame["return_5d"] = by_symbol["close"].transform(lambda series: series.pct_change(5))
        frame["momentum_10d"] = by_symbol["close"].transform(lambda series: series.pct_change(10))
        frame["momentum_20d"] = by_symbol["close"].transform(lambda series: series.pct_change(20))
        frame["volatility_10d"] = frame.groupby("ts_code")["return_1d"].transform(
            lambda series: series.rolling(10, min_periods=10).std()
        )

        frame["ma5"] = by_symbol["close"].transform(lambda series: series.rolling(5, min_periods=5).mean())
        frame["ma10"] = by_symbol["close"].transform(lambda series: series.rolling(10, min_periods=10).mean())
        frame["ma20"] = by_symbol["close"].transform(lambda series: series.rolling(20, min_periods=20).mean())

        for period in (5, 10, 20):
            ma_column = f"ma{period}"
            bias_column = f"ma{period}_bias"
            frame[bias_column] = frame["close"] / frame[ma_column] - 1

        frame["volume_ratio_5d"] = frame["volume"] / by_symbol["volume"].transform(
            lambda series: series.rolling(5, min_periods=5).mean()
        )
        frame["volume_change_5d"] = by_symbol["volume"].transform(lambda series: series.pct_change(5))
        frame["amount_change_5d"] = by_symbol["amount"].transform(lambda series: series.pct_change(5))

        macd_frame = pd.DataFrame(index=frame.index, columns=["macd", "macd_signal", "macd_hist"], dtype=float)
        for _, group in frame.groupby("ts_code"):
            macd_part = self._calculate_macd(group)
            macd_frame.loc[group.index, ["macd", "macd_signal", "macd_hist"]] = macd_part[
                ["macd", "macd_signal", "macd_hist"]
            ].values

        frame["macd"] = macd_frame["macd"]
        frame["macd_signal"] = macd_frame["macd_signal"]
        frame["macd_hist"] = macd_frame["macd_hist"]

        if "net_mf_amount" not in frame.columns:
            frame["net_mf_amount"] = pd.NA
        frame["net_mf_ratio"] = frame["net_mf_amount"] / frame["amount"].replace(0, pd.NA)
        return frame

    def _calculate_macd(self, frame: pd.DataFrame) -> pd.DataFrame:
        close = frame["close"].astype(float)
        ema_fast = close.ewm(span=12, adjust=False).mean()
        ema_slow = close.ewm(span=26, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=9, adjust=False).mean()
        return pd.DataFrame(
            {
                "macd": macd,
                "macd_signal": signal,
                "macd_hist": macd - signal,
            },
            index=frame.index,
        )
