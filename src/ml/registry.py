DEFAULT_FEATURE_COLUMNS = [
    "return_1d",
    "return_5d",
    "momentum_10d",
    "momentum_20d",
    "volatility_10d",
    "ma5_bias",
    "ma10_bias",
    "ma20_bias",
    "macd",
    "macd_signal",
    "macd_hist",
    "volume_ratio_5d",
    "volume_change_5d",
    "amount_change_5d",
    "turnover_rate",
    "pe",
    "pb",
    "net_mf_amount",
    "net_mf_ratio",
    "top_list_flag",
]

DEFAULT_LABEL_COLUMN = "future_excess_return"
DEFAULT_SCORE_COLUMN = "ml_score"

MODEL_LABELS = {
    "linear_factor": "线性因子评分",
    "sklearn_ridge": "Sklearn Ridge 回归",
    "compare": "双模型对照实验",
}

META_COLUMNS = [
    "ts_code",
    "trade_date",
    "buy_date",
    "sell_date",
    "open",
    "close",
    "high",
    "low",
    "volume",
    "amount",
    "entry_open",
    "exit_close",
    "future_return",
    "future_excess_return",
]
