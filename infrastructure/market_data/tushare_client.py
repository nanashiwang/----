from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import io
import importlib
from contextlib import redirect_stderr, redirect_stdout
from typing import Any


class TushareMarketDataClient:
    def __init__(self, token: str = '', api_url: str = '', default_watchlist: list[str] | None = None):
        self.token = token
        self.api_url = api_url
        self.default_watchlist = default_watchlist or []
        self._pro = None
        ts_module = self._optional_import('tushare')
        if token and ts_module is not None:
            self._pro = ts_module.pro_api(token)
            if api_url:
                self._pro._DataApi__http_url = api_url.rstrip('/') + '/'

    def get_watchlist_symbols(self) -> list[str]:
        return self.default_watchlist or ['000001.SZ', '600519.SH', '300750.SZ']

    def fetch_hot_news(self, as_of_date: date, hours: int = 24) -> list[dict[str, Any]]:
        if self._pro is None:
            return [
                {
                    'source': 'stub_news',
                    'title': f'{symbol} related sector rotation signal',
                    'url': f'https://example.com/{symbol.lower()}',
                    'published_at': datetime.combine(as_of_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=9 + index),
                    'summary': 'Placeholder news used when Tushare is unavailable.',
                    'content': 'Market discussion and sector catalyst placeholder.',
                    'symbols': [symbol],
                    'metadata': {'stub': True},
                }
                for index, symbol in enumerate(self.get_watchlist_symbols()[:3])
            ]

        start_dt = datetime.combine(as_of_date, datetime.min.time()) - timedelta(hours=hours)
        frame = self._pro.news(
            start_date=start_dt.strftime('%Y-%m-%d %H:%M:%S'),
            end_date=datetime.combine(as_of_date, datetime.max.time()).strftime('%Y-%m-%d %H:%M:%S'),
            src='sina',
        )
        if frame is None or frame.empty:
            return []

        rows = []
        for row in frame.to_dict('records'):
            rows.append(
                {
                    'source': row.get('src', 'tushare_news'),
                    'title': row.get('title', ''),
                    'url': row.get('url', ''),
                    'published_at': self._parse_datetime(row.get('datetime')),
                    'summary': row.get('content', '')[:200],
                    'content': row.get('content', ''),
                    'symbols': [],
                    'metadata': {'channel': row.get('channels', '')},
                }
            )
        return rows

    def fetch_market_snapshot(self, symbols: list[str], as_of_date: date) -> dict[str, dict[str, Any]]:
        snapshot = {}
        for index, symbol in enumerate(symbols, start=1):
            snapshot[symbol] = {
                'symbol': symbol,
                'as_of_date': as_of_date.isoformat(),
                'close': 10.0 + index,
                'pct_chg': round(0.5 * index, 2),
                'turnover_rate': round(1.2 + index * 0.3, 2),
                'volume_ratio': round(0.8 + index * 0.2, 2),
            }
        return snapshot

    def fetch_indicator_snapshot(self, symbols: list[str], as_of_date: date) -> dict[str, dict[str, Any]]:
        snapshot = {}
        for index, symbol in enumerate(symbols, start=1):
            snapshot[symbol] = {
                'symbol': symbol,
                'as_of_date': as_of_date.isoformat(),
                'ma5_bias': round(0.1 * index, 4),
                'ma20_bias': round(0.05 * index, 4),
                'rsi14': min(80, 45 + index * 5),
                'macd_hist': round(0.03 * index, 4),
            }
        return snapshot

    def load_realized_outcomes(self, symbols: list[str], as_of_date: date, horizon: int = 5) -> dict[str, dict[str, Any]]:
        review_horizons = sorted({1, 3, 5, horizon})
        max_horizon = max(review_horizons)
        benchmark_closes = self._load_price_path('000300.SH', as_of_date, max_horizon, benchmark=True)
        benchmark_returns = self._calculate_horizon_returns(benchmark_closes, review_horizons) if benchmark_closes else {}
        outcomes: dict[str, dict[str, Any]] = {}

        for symbol in symbols:
            closes = self._load_price_path(symbol, as_of_date, max_horizon)
            if len(closes) <= max_horizon:
                outcomes[symbol] = {
                    'symbol': symbol,
                    'buy_date': as_of_date.isoformat(),
                    'status': 'insufficient_data',
                    'error': 'price data is unavailable for the requested review horizon',
                }
                continue

            horizon_returns = self._calculate_horizon_returns(closes, review_horizons)
            selected_return = horizon_returns.get(horizon)
            benchmark_return = benchmark_returns.get(horizon)
            outcomes[symbol] = {
                'symbol': symbol,
                'buy_date': as_of_date.isoformat(),
                'sell_date': (as_of_date + timedelta(days=horizon)).isoformat(),
                'status': 'ok',
                'actual_return_1d': horizon_returns.get(1),
                'actual_return_3d': horizon_returns.get(3),
                'actual_return_5d': horizon_returns.get(5),
                'benchmark_return': benchmark_return,
                'benchmark_returns': benchmark_returns,
                'max_drawdown': self._calculate_max_drawdown(closes[: horizon + 1]),
                'future_return': selected_return,
                'future_excess_return': round(selected_return - benchmark_return, 4)
                if selected_return is not None and benchmark_return is not None
                else None,
                'price_source': 'tushare' if self._pro is not None else 'stub_market_data',
            }
        return outcomes

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if value in (None, ''):
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        text = str(value).replace('T', ' ')
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                return datetime.strptime(text[:19], fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None

    @staticmethod
    def _optional_import(module_name: str):
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                return importlib.import_module(module_name)
        except Exception:
            return None

    def _load_price_path(self, symbol: str, as_of_date: date, horizon: int, benchmark: bool = False) -> list[float]:
        if symbol.upper().startswith('MISSING'):
            return []

        if self._pro is not None:
            try:
                end_date = (as_of_date + timedelta(days=horizon + 10)).strftime('%Y%m%d')
                start_date = as_of_date.strftime('%Y%m%d')
                frame = (
                    self._pro.index_daily(ts_code=symbol, start_date=start_date, end_date=end_date)
                    if benchmark and hasattr(self._pro, 'index_daily')
                    else self._pro.daily(ts_code=symbol, start_date=start_date, end_date=end_date)
                )
                if frame is not None and not frame.empty:
                    frame = frame.sort_values('trade_date')
                    closes = [float(item) for item in frame['close'].tolist()]
                    if len(closes) > horizon:
                        return closes[: horizon + 1]
            except Exception:
                pass

        return self._build_stub_price_path(symbol, horizon, benchmark=benchmark)

    @staticmethod
    def _build_stub_price_path(symbol: str, horizon: int, benchmark: bool = False) -> list[float]:
        seed = sum(ord(char) for char in symbol)
        base_price = 100.0 if benchmark else 10.0 + (seed % 40)
        drift = 0.002 if benchmark else ((seed % 9) - 4) * 0.003
        closes = [round(base_price, 4)]
        for day in range(1, horizon + 1):
            wobble = (((seed + day * 13) % 7) - 3) * 0.0025
            closes.append(round(closes[-1] * (1 + drift + wobble), 4))
        return closes

    @staticmethod
    def _calculate_horizon_returns(closes: list[float], horizons: list[int]) -> dict[int, float]:
        returns = {}
        if not closes:
            return returns
        start_price = closes[0]
        for horizon in horizons:
            if len(closes) <= horizon:
                returns[horizon] = None
                continue
            returns[horizon] = round(closes[horizon] / start_price - 1.0, 4)
        return returns

    @staticmethod
    def _calculate_max_drawdown(closes: list[float]) -> float | None:
        if not closes:
            return None
        peak = closes[0]
        max_drawdown = 0.0
        for close in closes:
            peak = max(peak, close)
            drawdown = close / peak - 1.0
            max_drawdown = min(max_drawdown, drawdown)
        return round(max_drawdown, 4)
