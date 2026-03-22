from typing import Any, Dict, List

from pydantic import BaseModel, Field


class MarketDataOverviewOut(BaseModel):
    symbols: List[str] = Field(default_factory=list)
    ts_code: str = ""
    data_types: List[str] = Field(default_factory=list)
    benchmark_index_codes: List[str] = Field(default_factory=list)
    primary_benchmark: str = ""
    records: List[Dict[str, Any]] = Field(default_factory=list)
    price_series: List[Dict[str, Any]] = Field(default_factory=list)
    benchmark_series: List[Dict[str, Any]] = Field(default_factory=list)
    latest_summary: Dict[str, Any] = Field(default_factory=dict)
    benchmark_summary: Dict[str, Any] = Field(default_factory=dict)
    sync_window: Dict[str, Any] = Field(default_factory=dict)
    runtime: Dict[str, Any] = Field(default_factory=dict)


class StockSearchItemOut(BaseModel):
    ts_code: str
    symbol: str = ""
    name: str = ""
    area: str = ""
    industry: str = ""
    market: str = ""


class StockSearchOut(BaseModel):
    query: str = ""
    market: str = ""
    area: str = ""
    industry: str = ""
    total: int = 0
    items: List[StockSearchItemOut] = Field(default_factory=list)
    markets: List[str] = Field(default_factory=list)
    areas: List[str] = Field(default_factory=list)
    industries: List[str] = Field(default_factory=list)


class MarketDataSyncResult(BaseModel):
    success: bool
    status: str = ""
    message: str = ""
    mode: str = "incremental"
    symbol_count: int = 0
    symbols: List[str] = Field(default_factory=list)
    data_types: List[str] = Field(default_factory=list)
    daily_rows: int = 0
    snapshot_rows: int = 0
    index_rows: int = 0
    benchmark_index_codes: List[str] = Field(default_factory=list)
    primary_benchmark: str = ""
    range_start: str = ""
    range_end: str = ""
    errors: List[str] = Field(default_factory=list)


class MarketDataSyncRequest(BaseModel):
    mode: str = "incremental"


class MarketDataSyncStartOut(BaseModel):
    sync_id: str
    status: str = "started"
    mode: str = "incremental"
    message: str = ""
    reused: bool = False


class MarketDataSyncStatusOut(BaseModel):
    sync_id: str = ""
    status: str = "unknown"
    mode: str = "incremental"
    message: str = ""
    progress: int = 0
    current: int = 0
    total: int = 0
    current_task: str = ""
    errors: List[str] = Field(default_factory=list)
    started_at: str = ""
    updated_at: str = ""
    result: Dict[str, Any] = Field(default_factory=dict)
