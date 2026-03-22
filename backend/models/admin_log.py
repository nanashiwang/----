from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AdminUsageLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: str
    user_role: str = "user"
    module: str
    module_label: str = ""
    action: str
    action_label: str = ""
    method: str
    status: str = "success"
    status_label: str = ""
    label_column: str = ""
    symbols_count: int = 0
    date_range_start: str = ""
    date_range_end: str = ""
    primary_metric_name: str = ""
    primary_metric_label: str = ""
    primary_metric_value: Optional[float] = None
    secondary_metric_name: str = ""
    secondary_metric_label: str = ""
    secondary_metric_value: Optional[float] = None
    error_message: str = ""
    parameters: Dict[str, Any] = Field(default_factory=dict)
    result_summary: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""


class AdminUsageRankingOut(BaseModel):
    name: str
    module: str = ""
    module_label: str = ""
    metric_name: str = ""
    metric_label: str = ""
    run_count: int = 0
    avg_value: Optional[float] = None
    best_value: Optional[float] = None


class AdminUsageSummaryOut(BaseModel):
    total_runs: int = 0
    success_runs: int = 0
    failed_runs: int = 0
    unique_users: int = 0
    positive_primary_runs: int = 0
    latest_run_at: str = ""
    average_primary_value: Optional[float] = None
    best_run: Dict[str, Any] = Field(default_factory=dict)
    module_breakdown: List[AdminUsageRankingOut] = Field(default_factory=list)
    method_rankings: List[AdminUsageRankingOut] = Field(default_factory=list)


class AdminUsageLogListOut(BaseModel):
    items: List[AdminUsageLogOut] = Field(default_factory=list)
    summary: AdminUsageSummaryOut = Field(default_factory=AdminUsageSummaryOut)

