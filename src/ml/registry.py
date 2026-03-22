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
    "benchmark_return_1d",
    "benchmark_return_5d",
    "benchmark_momentum_20d",
    "relative_strength_1d",
    "relative_strength_5d",
    "excess_momentum_20d",
    "turnover_rate",
    "pe",
    "pb",
    "net_mf_amount",
    "net_mf_ratio",
    "top_list_flag",
]

DEFAULT_LABEL_COLUMN = "future_excess_return"
DEFAULT_SCORE_COLUMN = "ml_score"

FEATURE_LABELS = {
    "return_1d": "1日收益率",
    "return_5d": "5日收益率",
    "momentum_10d": "10日动量",
    "momentum_20d": "20日动量",
    "volatility_10d": "10日波动率",
    "ma5_bias": "MA5 偏离",
    "ma10_bias": "MA10 偏离",
    "ma20_bias": "MA20 偏离",
    "macd": "MACD DIF",
    "macd_signal": "MACD DEA",
    "macd_hist": "MACD 柱体",
    "volume_ratio_5d": "5日量比",
    "volume_change_5d": "5日成交量变化",
    "amount_change_5d": "5日成交额变化",
    "benchmark_return_1d": "基准1日收益率",
    "benchmark_return_5d": "基准5日收益率",
    "benchmark_momentum_20d": "基准20日动量",
    "relative_strength_1d": "相对大盘1日强弱",
    "relative_strength_5d": "相对大盘5日强弱",
    "excess_momentum_20d": "相对大盘20日动量",
    "turnover_rate": "换手率",
    "pe": "市盈率 PE",
    "pb": "市净率 PB",
    "net_mf_amount": "主力净流入额",
    "net_mf_ratio": "主力净流入占比",
    "top_list_flag": "龙虎榜事件标记",
}

FEATURE_DESCRIPTIONS = {
    "return_1d": "短线涨跌幅，适合观察隔日强弱。",
    "return_5d": "5 个交易日累计收益率。",
    "momentum_10d": "10 个交易日趋势强度。",
    "momentum_20d": "20 个交易日趋势强度。",
    "volatility_10d": "近 10 日波动水平。",
    "ma5_bias": "收盘价相对 5 日均线的偏离。",
    "ma10_bias": "收盘价相对 10 日均线的偏离。",
    "ma20_bias": "收盘价相对 20 日均线的偏离。",
    "macd": "MACD 快慢线差值。",
    "macd_signal": "MACD 信号线。",
    "macd_hist": "MACD 柱体强弱。",
    "volume_ratio_5d": "当前成交量相对 5 日均量。",
    "volume_change_5d": "成交量相对 5 日前的变化。",
    "amount_change_5d": "成交额相对 5 日前的变化。",
    "benchmark_return_1d": "主基准指数的 1 日收益率。",
    "benchmark_return_5d": "主基准指数的 5 日收益率。",
    "benchmark_momentum_20d": "主基准指数的 20 日趋势强度。",
    "relative_strength_1d": "个股 1 日收益减去主基准 1 日收益。",
    "relative_strength_5d": "个股 5 日收益减去主基准 5 日收益。",
    "excess_momentum_20d": "个股 20 日动量减去主基准 20 日动量。",
    "turnover_rate": "筹码换手活跃度。",
    "pe": "估值水平。",
    "pb": "净资产相对估值。",
    "net_mf_amount": "主力资金净流入金额。",
    "net_mf_ratio": "主力资金净流入占成交额比例。",
    "top_list_flag": "是否出现龙虎榜事件。",
}

LABEL_LABELS = {
    "future_return": "未来持有期收益率",
    "future_excess_return": "未来持有期超额收益率",
    "future_benchmark_excess_return": "未来相对基准超额收益率",
}

LABEL_DESCRIPTIONS = {
    "future_return": "T 日收盘后信号，按 T+1 开盘买入并持有若干天后的收益率。",
    "future_excess_return": "未来收益率减去同日横截面平均收益率，更适合做选股排序。",
    "future_benchmark_excess_return": "未来收益率减去主基准同期收益率，更适合和 A 股大盘比较。",
}

MODEL_LABELS = {
    "linear_factor": "线性因子评分",
    "sklearn_ridge": "Ridge 回归",
    "sklearn_random_forest": "随机森林回归",
    "compare": "双模型对照实验",
}

MODEL_DESCRIPTIONS = {
    "linear_factor": "用因子 IC 构造线性权重，轻量、可解释、依赖最少。",
    "sklearn_ridge": "标准化后做 Ridge 回归，适合连续型收益预测。",
    "sklearn_random_forest": "树模型做非线性拟合，适合观察特征交互。",
}

TUNING_LABELS = {
    "none": "不调优",
    "grid_search": "网格搜索",
    "optuna": "Optuna",
}

TUNING_DESCRIPTIONS = {
    "none": "直接使用默认参数训练。",
    "grid_search": "在一组固定候选参数中搜索最优解。",
    "optuna": "用贝叶斯式试验搜索更优参数，需要安装 optuna。",
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
    "benchmark_entry_open",
    "benchmark_exit_close",
    "benchmark_future_return",
    "future_benchmark_excess_return",
]
