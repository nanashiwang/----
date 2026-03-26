from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BacktestRequest:
    run_id: str
    as_of_date: str
    symbols: list[str] = field(default_factory=list)
    hold_days: int = 5


class BacktestService:
    def run(self, request: BacktestRequest) -> dict[str, Any]:
        return {
            'run_id': request.run_id,
            'as_of_date': request.as_of_date,
            'symbols': request.symbols,
            'hold_days': request.hold_days,
            'status': 'backtest_skeleton_ready',
        }
