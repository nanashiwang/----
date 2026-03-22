import pandas as pd


class LabelBuilder:
    """基于未来价格表现构建监督学习标签。"""

    def build_labels(self, frame: pd.DataFrame, hold_days: int = 5) -> pd.DataFrame:
        if frame.empty:
            return frame

        labeled = frame.sort_values(["ts_code", "trade_date"]).copy()
        grouped = labeled.groupby("ts_code", group_keys=False)

        labeled["buy_date"] = grouped["trade_date"].shift(-1)
        labeled["sell_date"] = grouped["trade_date"].shift(-hold_days)
        labeled["entry_open"] = grouped["open"].shift(-1)
        labeled["exit_close"] = grouped["close"].shift(-hold_days)
        labeled["future_return"] = labeled["exit_close"] / labeled["entry_open"] - 1
        labeled["future_excess_return"] = labeled["future_return"] - labeled.groupby("trade_date")[
            "future_return"
        ].transform("mean")

        if "benchmark_open" in labeled.columns and "benchmark_close" in labeled.columns:
            benchmark_frame = (
                labeled[["trade_date", "benchmark_open", "benchmark_close"]]
                .dropna(subset=["trade_date"])
                .drop_duplicates(subset=["trade_date"], keep="last")
                .set_index("trade_date")
            )
            benchmark_open_map = benchmark_frame["benchmark_open"].to_dict()
            benchmark_close_map = benchmark_frame["benchmark_close"].to_dict()
            labeled["benchmark_entry_open"] = labeled["buy_date"].map(benchmark_open_map)
            labeled["benchmark_exit_close"] = labeled["sell_date"].map(benchmark_close_map)
            labeled["benchmark_future_return"] = (
                labeled["benchmark_exit_close"] / labeled["benchmark_entry_open"] - 1
            )
            labeled["future_benchmark_excess_return"] = (
                labeled["future_return"] - labeled["benchmark_future_return"]
            )
        else:
            labeled["benchmark_entry_open"] = pd.NA
            labeled["benchmark_exit_close"] = pd.NA
            labeled["benchmark_future_return"] = pd.NA
            labeled["future_benchmark_excess_return"] = pd.NA
        return labeled
