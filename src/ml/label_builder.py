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
        return labeled
