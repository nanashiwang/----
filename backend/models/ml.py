from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class MlChoiceItem(BaseModel):
    value: str
    label: str
    description: str = ""
    disabled: bool = False
    meta: Dict[str, Any] = Field(default_factory=dict)


class MlExperimentOptionsOut(BaseModel):
    cycle: str = "daily"
    cycle_label: str = "日线同周期"
    date_bounds: Dict[str, str] = Field(default_factory=dict)
    symbols: List[str] = Field(default_factory=list)
    feature_options: List[MlChoiceItem] = Field(default_factory=list)
    label_options: List[MlChoiceItem] = Field(default_factory=list)
    model_options: List[MlChoiceItem] = Field(default_factory=list)
    tuning_options: List[MlChoiceItem] = Field(default_factory=list)
    defaults: Dict[str, Any] = Field(default_factory=dict)
    runtime: Dict[str, Any] = Field(default_factory=dict)


class MlExperimentRequest(BaseModel):
    symbols: List[str] = Field(default_factory=list)
    feature_columns: List[str] = Field(default_factory=list)
    label_column: Literal["future_return", "future_excess_return", "future_benchmark_excess_return"] = "future_excess_return"
    model_type: Literal["linear_factor", "sklearn_ridge", "sklearn_random_forest"] = "linear_factor"
    tuning_method: Literal["none", "grid_search", "optuna"] = "none"
    train_start_date: str
    train_end_date: str
    predict_start_date: str
    predict_end_date: str
    hold_days: int = Field(default=5, ge=1, le=30)
    use_feature_selection: bool = True
    max_features: int = Field(default=8, ge=1, le=20)
    prediction_top_n: int = Field(default=20, ge=1, le=100)
    tuning_trials: int = Field(default=20, ge=5, le=200)

    @field_validator(
        "train_start_date",
        "train_end_date",
        "predict_start_date",
        "predict_end_date",
    )
    @classmethod
    def validate_date_text(cls, value: str) -> str:
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("日期格式必须为 YYYY-MM-DD") from exc
        return value

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, values: List[str]) -> List[str]:
        normalized = []
        seen = set()
        for value in values:
            symbol = str(value or "").strip().upper()
            if not symbol or symbol in seen:
                continue
            normalized.append(symbol)
            seen.add(symbol)
        return normalized

    @field_validator("feature_columns")
    @classmethod
    def normalize_features(cls, values: List[str]) -> List[str]:
        normalized = []
        seen = set()
        for value in values:
            feature = str(value or "").strip()
            if not feature or feature in seen:
                continue
            normalized.append(feature)
            seen.add(feature)
        return normalized

    @model_validator(mode="after")
    def validate_windows(self):
        train_start = datetime.strptime(self.train_start_date, "%Y-%m-%d")
        train_end = datetime.strptime(self.train_end_date, "%Y-%m-%d")
        predict_start = datetime.strptime(self.predict_start_date, "%Y-%m-%d")
        predict_end = datetime.strptime(self.predict_end_date, "%Y-%m-%d")

        if train_start > train_end:
            raise ValueError("训练时间范围不正确：开始日期不能晚于结束日期")
        if predict_start > predict_end:
            raise ValueError("预测时间范围不正确：开始日期不能晚于结束日期")
        if train_end >= predict_start:
            raise ValueError("训练结束日期必须早于预测开始日期，避免未来数据泄漏")
        return self


class MlExperimentResultOut(BaseModel):
    cycle: str = "daily"
    error: str = ""
    params: Dict[str, Any] = Field(default_factory=dict)
    sample_summary: Dict[str, Any] = Field(default_factory=dict)
    selected_features: List[str] = Field(default_factory=list)
    feature_stats: List[Dict[str, Any]] = Field(default_factory=list)
    model_weights: List[Dict[str, Any]] = Field(default_factory=list)
    training_summary: Dict[str, Any] = Field(default_factory=dict)
    tuning_summary: Dict[str, Any] = Field(default_factory=dict)
    prediction_summary: Dict[str, Any] = Field(default_factory=dict)
    predictions: List[Dict[str, Any]] = Field(default_factory=list)
