from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import pandas as pd

from ..data.db.sqlite_client import SQLiteClient
from ..ml.dataset_builder import DatasetBuilder
from ..ml.predictor import LinearFactorPredictor, SklearnModelPredictor
from ..ml.registry import DEFAULT_FEATURE_COLUMNS, DEFAULT_LABEL_COLUMN, DEFAULT_SCORE_COLUMN, MODEL_LABELS
from ..ml.selector import FeatureSelector
from ..ml.trainer import LinearFactorTrainer, SklearnRidgeTrainer
from .metrics import build_equity_curve, summarize_backtest


@dataclass(frozen=True)
class TradePath:
    ts_code: str
    signal_date: pd.Timestamp
    buy_date: pd.Timestamp
    sell_date: pd.Timestamp
    entry_price: float
    exit_price: float
    gross_return: float
    net_return: float
    daily_path: List[tuple[pd.Timestamp, float]]
    score: float


class PortfolioBacktestEngine:
    """标准信号回测引擎：先训练线性因子，再做等权组合回测。"""

    def __init__(self, sqlite_client: SQLiteClient):
        self.db = sqlite_client
        self.dataset_builder = DatasetBuilder(sqlite_client)
        self.selector = FeatureSelector()
        self.linear_trainer = LinearFactorTrainer()
        self.linear_predictor = LinearFactorPredictor()
        self.sklearn_trainer = SklearnRidgeTrainer()
        self.sklearn_predictor = SklearnModelPredictor()

    def run_factor_backtest(
        self,
        start_date: str,
        end_date: str,
        symbols: Optional[Iterable[str]] = None,
        hold_days: int = 5,
        top_n: int = 5,
        fee_rate: float = 0.0005,
        slippage_rate: float = 0.0005,
        train_window_days: int = 120,
        max_features: int = 6,
        model_type: str = "linear_factor",
    ) -> Dict:
        start_dt = pd.Timestamp(start_date)
        end_dt = pd.Timestamp(end_date)
        if start_dt > end_dt:
            raise ValueError("回测时间范围不正确：开始日期不能晚于结束日期")

        symbol_list = self._resolve_symbols(symbols=symbols, start_date=start_date, end_date=end_date)
        if not symbol_list:
            raise ValueError("标准回测失败：当前时间范围内没有可用股票数据")

        query_start_dt = start_dt - pd.Timedelta(days=max(train_window_days * 2, 120))
        query_end_dt = end_dt + pd.Timedelta(days=max(hold_days * 3, 15))
        dataset = self.dataset_builder.build_dataset(
            symbols=symbol_list,
            query_start_date=query_start_dt.strftime("%Y-%m-%d"),
            query_end_date=query_end_dt.strftime("%Y-%m-%d"),
            signal_start_date=query_start_dt.strftime("%Y-%m-%d"),
            signal_end_date=end_dt.strftime("%Y-%m-%d"),
            hold_days=hold_days,
        )
        if dataset.empty:
            raise ValueError("标准回测失败：本地 SQLite 还没有足够的行情样本")

        training_start_dt = start_dt - pd.Timedelta(days=train_window_days)
        training_df = dataset[
            (dataset["trade_date"] >= training_start_dt)
            & (dataset["trade_date"] < start_dt)
            & dataset["sell_date"].notna()
            & (dataset["sell_date"] < start_dt)
        ].copy()
        test_df = dataset[
            (dataset["trade_date"] >= start_dt)
            & (dataset["trade_date"] <= end_dt)
            & dataset["buy_date"].notna()
            & dataset["sell_date"].notna()
        ].copy()

        if training_df.empty:
            raise ValueError("标准回测失败：训练窗口内样本不足，请先拉取更长历史数据")
        if test_df.empty:
            raise ValueError("标准回测失败：回测窗口内没有可交易样本")

        selection = self.selector.select(
            training_df,
            candidate_features=DEFAULT_FEATURE_COLUMNS,
            label_col=DEFAULT_LABEL_COLUMN,
            top_k=max_features,
        )
        selected_features = selection["selected_features"]
        if not selected_features:
            raise ValueError("标准回测失败：没有筛选出可用指标，请扩大历史窗口或补齐更多数据")

        full_market_frame = self.dataset_builder.feature_builder.load_market_frame(
            symbols=symbol_list,
            start_date=query_start_dt.strftime("%Y-%m-%d"),
            end_date=query_end_dt.strftime("%Y-%m-%d"),
        )
        raw_prices = full_market_frame[["ts_code", "trade_date", "open", "close"]].drop_duplicates().copy()
        if model_type == "compare":
            experiments = [
                self._run_single_model_backtest(
                    model_type=current_model_type,
                    training_df=training_df,
                    test_df=test_df,
                    raw_prices=raw_prices,
                    selected_features=selected_features,
                    feature_stats=selection["feature_stats"],
                    start_date=start_date,
                    end_date=end_date,
                    symbols=symbol_list,
                    hold_days=hold_days,
                    top_n=top_n,
                    fee_rate=fee_rate,
                    slippage_rate=slippage_rate,
                    train_window_days=train_window_days,
                    max_features=max_features,
                )
                for current_model_type in ("linear_factor", "sklearn_ridge")
            ]
            return self._build_comparison_result(
                experiments=experiments,
                selected_features=selected_features,
                feature_stats=selection["feature_stats"],
                training_df=training_df,
                test_df=test_df,
            )

        return self._run_single_model_backtest(
            model_type=model_type,
            training_df=training_df,
            test_df=test_df,
            raw_prices=raw_prices,
            selected_features=selected_features,
            feature_stats=selection["feature_stats"],
            start_date=start_date,
            end_date=end_date,
            symbols=symbol_list,
            hold_days=hold_days,
            top_n=top_n,
            fee_rate=fee_rate,
            slippage_rate=slippage_rate,
            train_window_days=train_window_days,
            max_features=max_features,
        )

    def _run_single_model_backtest(
        self,
        *,
        model_type: str,
        training_df: pd.DataFrame,
        test_df: pd.DataFrame,
        raw_prices: pd.DataFrame,
        selected_features: List[str],
        feature_stats: List[Dict],
        start_date: str,
        end_date: str,
        symbols: List[str],
        hold_days: int,
        top_n: int,
        fee_rate: float,
        slippage_rate: float,
        train_window_days: int,
        max_features: int,
    ) -> Dict:
        model = self._fit_model(
            model_type=model_type,
            training_df=training_df,
            selected_features=selected_features,
            feature_stats=feature_stats,
        )
        scored_test = self._predict_scores(model_type=model_type, test_df=test_df, model=model)
        scored_test = scored_test.dropna(subset=[DEFAULT_SCORE_COLUMN, "buy_date", "sell_date"]).copy()
        if scored_test.empty:
            raise ValueError("标准回测失败：评分阶段没有产出有效信号")

        trade_result = self._build_portfolio_results(
            scored_test=scored_test,
            raw_prices=raw_prices,
            hold_days=hold_days,
            top_n=top_n,
            fee_rate=fee_rate,
            slippage_rate=slippage_rate,
        )
        summary = summarize_backtest(
            equity_curve=trade_result["equity_curve"],
            trades=trade_result["trades"],
            turnover_series=trade_result["turnover_series"],
        )

        return {
            "mode": "portfolio",
            "model_type": model_type,
            "strategy_name": f"{MODEL_LABELS.get(model_type, model_type)} + 等权组合",
            "summary": summary,
            "params": {
                "start_date": start_date,
                "end_date": end_date,
                "hold_days": hold_days,
                "top_n": top_n,
                "fee_rate": fee_rate,
                "slippage_rate": slippage_rate,
                "train_window_days": train_window_days,
                "max_features": max_features,
                "symbols": symbols,
                "model_type": model_type,
            },
            "selected_features": selected_features,
            "feature_stats": feature_stats,
            "model_weights": self._build_model_weights(model),
            "training_summary": {
                "train_start_date": training_df["trade_date"].min().strftime("%Y-%m-%d"),
                "train_end_date": training_df["trade_date"].max().strftime("%Y-%m-%d"),
                "train_samples": int(len(training_df)),
                "test_samples": int(len(scored_test)),
                "train_score": float(model.get("train_score", 0.0)),
            },
            "equity_curve": [
                {
                    "trade_date": row["trade_date"].strftime("%Y-%m-%d"),
                    "nav": float(row["nav"]),
                    "benchmark_nav": float(row["benchmark_nav"]),
                    "daily_return": float(row["daily_return"]),
                    "benchmark_return": float(row["benchmark_return"]),
                    "drawdown": float(row["drawdown"]),
                }
                for _, row in trade_result["equity_curve"].iterrows()
            ],
            "trades": trade_result["trades"],
        }

    def _fit_model(
        self,
        *,
        model_type: str,
        training_df: pd.DataFrame,
        selected_features: List[str],
        feature_stats: List[Dict],
    ) -> Dict:
        if model_type == "linear_factor":
            return self.linear_trainer.fit(
                training_df,
                selected_features,
                label_col=DEFAULT_LABEL_COLUMN,
                feature_stats=feature_stats,
            )
        if model_type == "sklearn_ridge":
            return self.sklearn_trainer.fit(
                training_df,
                selected_features,
                label_col=DEFAULT_LABEL_COLUMN,
            )
        raise ValueError(f"暂不支持的模型类型: {model_type}")

    def _predict_scores(self, *, model_type: str, test_df: pd.DataFrame, model: Dict) -> pd.DataFrame:
        if model_type == "linear_factor":
            return self.linear_predictor.predict(test_df, model, score_col=DEFAULT_SCORE_COLUMN)
        if model_type == "sklearn_ridge":
            return self.sklearn_predictor.predict(test_df, model, score_col=DEFAULT_SCORE_COLUMN)
        raise ValueError(f"暂不支持的模型类型: {model_type}")

    def _build_model_weights(self, model: Dict) -> List[Dict]:
        weights = model.get("weights", {})
        if not isinstance(weights, dict):
            return []
        ranked = sorted(weights.items(), key=lambda item: abs(item[1]), reverse=True)
        return [{"feature": feature, "weight": float(weight)} for feature, weight in ranked]

    def _build_comparison_result(
        self,
        *,
        experiments: List[Dict],
        selected_features: List[str],
        feature_stats: List[Dict],
        training_df: pd.DataFrame,
        test_df: pd.DataFrame,
    ) -> Dict:
        linear_result = next(item for item in experiments if item["model_type"] == "linear_factor")
        ridge_result = next(item for item in experiments if item["model_type"] == "sklearn_ridge")
        comparison_metric = "annualized_excess_return"
        winner = max(experiments, key=lambda item: item["summary"].get(comparison_metric, float("-inf")))

        return {
            "mode": "portfolio",
            "model_type": "compare",
            "strategy_name": MODEL_LABELS["compare"],
            "selected_features": selected_features,
            "feature_stats": feature_stats,
            "training_summary": {
                "train_start_date": training_df["trade_date"].min().strftime("%Y-%m-%d"),
                "train_end_date": training_df["trade_date"].max().strftime("%Y-%m-%d"),
                "train_samples": int(len(training_df)),
                "test_samples": int(len(test_df)),
            },
            "experiments": experiments,
            "comparison_summary": {
                "base_model": linear_result["model_type"],
                "candidate_model": ridge_result["model_type"],
                "winner": winner["model_type"],
                "metric": comparison_metric,
                "metric_label": "年化超额收益",
                "deltas": {
                    "cumulative_return": ridge_result["summary"]["cumulative_return"]
                    - linear_result["summary"]["cumulative_return"],
                    "annualized_return": ridge_result["summary"]["annualized_return"]
                    - linear_result["summary"]["annualized_return"],
                    "annualized_excess_return": ridge_result["summary"]["annualized_excess_return"]
                    - linear_result["summary"]["annualized_excess_return"],
                    "max_drawdown": ridge_result["summary"]["max_drawdown"]
                    - linear_result["summary"]["max_drawdown"],
                    "sharpe": ridge_result["summary"]["sharpe"] - linear_result["summary"]["sharpe"],
                },
            },
        }

    def _resolve_symbols(
        self,
        symbols: Optional[Iterable[str]],
        start_date: str,
        end_date: str,
    ) -> List[str]:
        symbol_list = [str(item).strip().upper() for item in (symbols or []) if str(item).strip()]
        if symbol_list:
            return list(dict.fromkeys(symbol_list))

        sql = """
            SELECT DISTINCT ts_code
            FROM stock_data
            WHERE trade_date BETWEEN ? AND ?
            ORDER BY ts_code
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(sql, (start_date, end_date)).fetchall()
        return [row["ts_code"] for row in rows]

    def _build_portfolio_results(
        self,
        scored_test: pd.DataFrame,
        raw_prices: pd.DataFrame,
        hold_days: int,
        top_n: int,
        fee_rate: float,
        slippage_rate: float,
    ) -> Dict:
        price_lookup = {
            ts_code: frame.sort_values("trade_date").reset_index(drop=True)
            for ts_code, frame in raw_prices.groupby("ts_code")
        }
        path_cache: Dict[tuple[str, pd.Timestamp, pd.Timestamp], TradePath] = {}
        strategy_cohorts: List[List[TradePath]] = []
        benchmark_cohorts: List[List[TradePath]] = []

        grouped = scored_test.sort_values(["trade_date", DEFAULT_SCORE_COLUMN], ascending=[True, False]).groupby(
            "trade_date"
        )
        for signal_date, frame in grouped:
            candidates: List[TradePath] = []
            for row in frame.to_dict("records"):
                trade_key = (row["ts_code"], row["buy_date"], row["sell_date"])
                if trade_key not in path_cache:
                    trade_path = self._build_trade_path(
                        ts_code=row["ts_code"],
                        signal_date=signal_date,
                        buy_date=row["buy_date"],
                        sell_date=row["sell_date"],
                        score=row[DEFAULT_SCORE_COLUMN],
                        price_frame=price_lookup.get(row["ts_code"]),
                        fee_rate=fee_rate,
                        slippage_rate=slippage_rate,
                    )
                    if trade_path is not None:
                        path_cache[trade_key] = trade_path
                trade_path = path_cache.get(trade_key)
                if trade_path is not None:
                    candidates.append(trade_path)

            if not candidates:
                continue

            strategy_cohorts.append(candidates[:top_n])
            benchmark_cohorts.append(candidates)

        if not strategy_cohorts:
            raise ValueError("标准回测失败：没有形成有效的调仓信号")

        min_buy_date = min(item.buy_date for cohort in strategy_cohorts for item in cohort)
        max_sell_date = max(item.sell_date for cohort in strategy_cohorts for item in cohort)
        all_dates = sorted(
            raw_prices[
                (raw_prices["trade_date"] >= min_buy_date) & (raw_prices["trade_date"] <= max_sell_date)
            ]["trade_date"].drop_duplicates()
        )
        strategy_returns = pd.Series(0.0, index=all_dates, dtype=float)
        benchmark_returns = pd.Series(0.0, index=all_dates, dtype=float)
        turnover_series = pd.Series(0.0, index=all_dates, dtype=float)
        trade_details: List[Dict] = []

        self._accumulate_cohort_returns(
            target_returns=strategy_returns,
            turnover_series=turnover_series,
            cohorts=strategy_cohorts,
            hold_days=hold_days,
            collect_trade_details=True,
            trade_details=trade_details,
        )
        self._accumulate_cohort_returns(
            target_returns=benchmark_returns,
            turnover_series=None,
            cohorts=benchmark_cohorts,
            hold_days=hold_days,
            collect_trade_details=False,
            trade_details=None,
        )

        equity_curve = build_equity_curve(strategy_returns, benchmark_returns)
        return {
            "equity_curve": equity_curve,
            "turnover_series": turnover_series,
            "trades": trade_details,
        }

    def _accumulate_cohort_returns(
        self,
        target_returns: pd.Series,
        turnover_series: Optional[pd.Series],
        cohorts: List[List[TradePath]],
        hold_days: int,
        collect_trade_details: bool,
        trade_details: Optional[List[Dict]],
    ) -> None:
        cohort_capital = 1.0 / hold_days
        for cohort in cohorts:
            if not cohort:
                continue
            position_weight = cohort_capital / len(cohort)
            for trade in cohort:
                for trade_date, daily_return in trade.daily_path:
                    if trade_date in target_returns.index:
                        target_returns.loc[trade_date] += position_weight * daily_return

                if turnover_series is not None:
                    if trade.buy_date in turnover_series.index:
                        turnover_series.loc[trade.buy_date] += position_weight
                    if trade.sell_date in turnover_series.index:
                        turnover_series.loc[trade.sell_date] += position_weight

                if collect_trade_details and trade_details is not None:
                    trade_details.append(
                        {
                            "signal_date": trade.signal_date.strftime("%Y-%m-%d"),
                            "buy_date": trade.buy_date.strftime("%Y-%m-%d"),
                            "sell_date": trade.sell_date.strftime("%Y-%m-%d"),
                            "ts_code": trade.ts_code,
                            "score": float(trade.score),
                            "weight": float(position_weight),
                            "entry_price": float(trade.entry_price),
                            "exit_price": float(trade.exit_price),
                            "gross_return": float(trade.gross_return),
                            "net_return": float(trade.net_return),
                        }
                    )

    def _build_trade_path(
        self,
        ts_code: str,
        signal_date: pd.Timestamp,
        buy_date: pd.Timestamp,
        sell_date: pd.Timestamp,
        score: float,
        price_frame: Optional[pd.DataFrame],
        fee_rate: float,
        slippage_rate: float,
    ) -> Optional[TradePath]:
        if price_frame is None or pd.isna(buy_date) or pd.isna(sell_date):
            return None

        trade_frame = price_frame[
            (price_frame["trade_date"] >= buy_date) & (price_frame["trade_date"] <= sell_date)
        ].copy()
        if trade_frame.empty:
            return None

        trade_frame = trade_frame.sort_values("trade_date").reset_index(drop=True)
        if trade_frame.iloc[0]["trade_date"] != buy_date or trade_frame.iloc[-1]["trade_date"] != sell_date:
            return None

        entry_open = float(trade_frame.iloc[0]["open"])
        exit_close = float(trade_frame.iloc[-1]["close"])
        if entry_open <= 0 or exit_close <= 0:
            return None

        entry_price = entry_open * (1 + slippage_rate)
        shares = (1 - fee_rate) / entry_price
        daily_path: List[tuple[pd.Timestamp, float]] = []
        for idx, row in trade_frame.iterrows():
            trade_date = row["trade_date"]
            close_price = float(row["close"])
            if close_price <= 0:
                return None

            if len(trade_frame) == 1:
                final_value = shares * close_price * (1 - slippage_rate) * (1 - fee_rate)
                daily_return = final_value - 1.0
            elif idx == 0:
                end_value = shares * close_price
                daily_return = end_value - 1.0
            elif idx == len(trade_frame) - 1:
                previous_close = float(trade_frame.iloc[idx - 1]["close"])
                previous_value = shares * previous_close
                final_value = shares * close_price * (1 - slippage_rate) * (1 - fee_rate)
                daily_return = final_value / previous_value - 1.0
            else:
                previous_close = float(trade_frame.iloc[idx - 1]["close"])
                daily_return = close_price / previous_close - 1.0

            daily_path.append((trade_date, float(daily_return)))

        exit_price = exit_close * (1 - slippage_rate) * (1 - fee_rate)
        gross_return = exit_close / entry_open - 1.0
        net_return = shares * exit_close * (1 - slippage_rate) * (1 - fee_rate) - 1.0
        return TradePath(
            ts_code=ts_code,
            signal_date=pd.Timestamp(signal_date),
            buy_date=pd.Timestamp(buy_date),
            sell_date=pd.Timestamp(sell_date),
            entry_price=float(entry_price),
            exit_price=float(exit_price),
            gross_return=float(gross_return),
            net_return=float(net_return),
            daily_path=daily_path,
            score=float(score),
        )
