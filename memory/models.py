from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class KnowledgeThresholds:
    tests_survived: int = 10
    pass_rate: float = 0.65
    min_market_regimes: int = 2
    consecutive_failures: int = 3


@dataclass(slots=True)
class KnowledgePruningThresholds:
    low_coverage: int = 2
    high_conflict_rate: float = 0.5
    warning_conflict_rate: float = 0.25
    low_return_threshold: float = 0.0
    deprecate_return_threshold: float = -0.01
    high_fail_rate: float = 0.6
    archive_fail_rate: float = 0.8
    regime_drift_overlap_ratio: float = 0.5
