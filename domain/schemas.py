from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from core.enums import FlowType, KnowledgeStatus, KnowledgeTier, RecommendationAction, RiskLevel, RunStatus
from core.ids import generate_prefixed_id
from core.time import utcnow


class EvidenceRef(BaseModel):
    ref_id: str = Field(default_factory=lambda: generate_prefixed_id('evidence'))
    ref_type: str
    title: str = ''
    source: str = ''
    url: str = ''
    symbol: Optional[str] = None
    excerpt: str = ''
    published_at: Optional[datetime] = None
    score: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CandidateOut(BaseModel):
    symbol: str
    name: str = ''
    action: RecommendationAction = RecommendationAction.WATCH
    weight: float = 0.0
    ml_score: float = 0.0
    event_score: float = 0.0
    technical_score: float = 0.0
    debate_consensus_score: float = 0.0
    risk_adjusted_score: float = 0.0
    final_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.MEDIUM
    risk_flags: List[str] = Field(default_factory=list)
    reason: str = ''
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    market_regime_tags: List[str] = Field(default_factory=list)
    event_tags: List[str] = Field(default_factory=list)
    technical_pattern_tags: List[str] = Field(default_factory=list)
    risk_pattern_tags: List[str] = Field(default_factory=list)
    knowledge_refs: List[EvidenceRef] = Field(default_factory=list)
    knowledge_impact_json: List[Dict[str, Any]] = Field(default_factory=list)
    knowledge_match_score: float = 0.0
    knowledge_risk_penalty: float = 0.0
    knowledge_conflict_flag: bool = False

    @model_validator(mode='after')
    def validate_include_requires_evidence(self) -> 'CandidateOut':
        if self.action == RecommendationAction.INCLUDE and not self.evidence_refs:
            raise ValueError('include recommendations require evidence_refs')
        return self


class WorkflowTriggerIn(BaseModel):
    flow_type: Optional[FlowType] = None
    as_of_date: date
    force: bool = False
    trigger_source: str = 'manual'
    user_id: Optional[str] = None
    prompt_version: Optional[str] = None
    agent_version: Optional[str] = None
    feature_set_version: Optional[str] = None
    model_version: Optional[str] = None
    watchlist_symbols: List[str] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('watchlist_symbols')
    @classmethod
    def normalize_symbols(cls, values: List[str]) -> List[str]:
        return [value.strip().upper() for value in values if value and value.strip()]


class WorkflowRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    flow_type: FlowType
    status: RunStatus
    as_of_date: date
    prompt_version: str
    agent_version: str
    feature_set_version: str
    model_version: str
    idempotency_key: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_json: Dict[str, Any] = Field(default_factory=dict)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WorkflowLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    node_run_id: str
    run_id: str
    node_name: str
    agent_name: str
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RecommendationRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recommendation_id: str
    run_id: str
    prediction_artifact_id: Optional[str] = None
    symbol: str
    action: RecommendationAction
    weight: float
    final_score: float
    reason: str
    risk_flags_json: Dict[str, Any] = Field(default_factory=dict)
    evidence_json: Dict[str, Any] = Field(default_factory=dict)
    knowledge_refs: List[EvidenceRef] = Field(default_factory=list)
    knowledge_impact_json: List[Dict[str, Any]] = Field(default_factory=list)
    knowledge_match_score: float = 0.0
    knowledge_risk_penalty: float = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode='after')
    def populate_knowledge_fields(self) -> 'RecommendationRecordOut':
        if not self.knowledge_refs:
            self.knowledge_refs = [
                EvidenceRef.model_validate(item)
                for item in self.evidence_json.get('knowledge_refs', [])
            ]
        if not self.knowledge_impact_json:
            self.knowledge_impact_json = list(self.evidence_json.get('knowledge_impact_json', []))
        if self.knowledge_match_score == 0.0:
            self.knowledge_match_score = float(self.evidence_json.get('knowledge_match_score', 0.0))
        if self.knowledge_risk_penalty == 0.0:
            self.knowledge_risk_penalty = float(self.evidence_json.get('knowledge_risk_penalty', 0.0))
        return self


class TradeOCRResult(BaseModel):
    image_uri: str = ''
    broker: str = ''
    account: str = ''
    symbol: Optional[str] = None
    trade_date: Optional[date] = None
    side: str = ''
    price: Optional[float] = None
    quantity: Optional[int] = None
    fees: float = 0.0
    confidence: float = 0.0
    raw_text: str = ''
    normalized_fields: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


class RecommendationVerdict(BaseModel):
    recommendation_id: str
    symbol: str
    expected_action: RecommendationAction
    actual_return_1d: Optional[float] = None
    actual_return_3d: Optional[float] = None
    actual_return_5d: Optional[float] = None
    benchmark_return: Optional[float] = None
    max_drawdown: Optional[float] = None
    verdict: str
    key_success_factors: List[str] = Field(default_factory=list)
    key_failure_factors: List[str] = Field(default_factory=list)
    evidence_json: Dict[str, Any] = Field(default_factory=dict)
    error_json: Dict[str, Any] = Field(default_factory=dict)


class ReviewVerdict(BaseModel):
    target_run_id: str
    horizon: int = 5
    summary_text: str
    verdicts: List[RecommendationVerdict] = Field(default_factory=list)
    outcome: str = 'pending'
    knowledge_actions: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeItem(BaseModel):
    knowledge_id: str = Field(default_factory=lambda: generate_prefixed_id('knowledge'))
    lineage_id: str | None = None
    tier: KnowledgeTier = KnowledgeTier.HOT
    text: str
    category: str
    source_run_ids: List[str] = Field(default_factory=list)
    source_recommendation_ids: List[str] = Field(default_factory=list)
    tests_survived: int = 0
    pass_count: int = 0
    fail_count: int = 0
    pass_rate: float = 0.0
    status: KnowledgeStatus = KnowledgeStatus.ACTIVE
    promotion_reason: str = ''
    applicable_event_tags: List[str] = Field(default_factory=list)
    applicable_technical_tags: List[str] = Field(default_factory=list)
    applicable_market_regimes: List[str] = Field(default_factory=list)
    negative_match_tags: List[str] = Field(default_factory=list)
    evidence_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @model_validator(mode='after')
    def sync_knowledge_counters(self) -> 'KnowledgeItem':
        total_tests = self.pass_count + self.fail_count
        if not self.lineage_id:
            self.lineage_id = self.knowledge_id
        if total_tests and self.tests_survived == 0:
            self.tests_survived = total_tests
        if self.tests_survived > 0:
            self.pass_rate = round(self.pass_count / self.tests_survived, 4)
        return self


class ReviewReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    review_report_id: str
    review_id: Optional[str] = None
    run_id: str
    target_run_id: str
    as_of_date: date
    horizon: int
    summary_text: str
    verdicts_json: Dict[str, Any] = Field(default_factory=dict)
    metrics_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode='after')
    def populate_review_id(self) -> 'ReviewReportOut':
        if not self.review_id:
            self.review_id = self.review_report_id
        return self


class HotKnowledgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    knowledge_id: str
    lineage_id: str | None = None
    text: str
    category: str
    source_run_ids: List[str] = Field(default_factory=list)
    source_recommendation_ids: List[str] = Field(default_factory=list)
    tests_survived: int
    pass_count: int
    fail_count: int
    pass_rate: float
    status: KnowledgeStatus
    applicable_event_tags: List[str] = Field(default_factory=list)
    applicable_technical_tags: List[str] = Field(default_factory=list)
    applicable_market_regimes: List[str] = Field(default_factory=list)
    negative_match_tags: List[str] = Field(default_factory=list)
    evidence_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode='after')
    def populate_lineage_id(self) -> 'HotKnowledgeOut':
        if not self.lineage_id:
            self.lineage_id = self.knowledge_id
        return self


class ColdKnowledge(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    knowledge_id: str
    lineage_id: str | None = None
    source_hot_knowledge_id: str
    text: str
    category: str
    promotion_reason: str
    promotion_run_id: str
    source_run_ids: List[str] = Field(default_factory=list)
    source_recommendation_ids: List[str] = Field(default_factory=list)
    tests_survived: int
    pass_count: int
    fail_count: int
    pass_rate: float
    applicable_event_tags: List[str] = Field(default_factory=list)
    applicable_technical_tags: List[str] = Field(default_factory=list)
    applicable_market_regimes: List[str] = Field(default_factory=list)
    negative_match_tags: List[str] = Field(default_factory=list)
    invalid_conditions: Dict[str, Any] = Field(default_factory=dict)
    status: KnowledgeStatus
    version: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode='after')
    def populate_lineage_id(self) -> 'ColdKnowledge':
        if not self.lineage_id:
            self.lineage_id = self.source_hot_knowledge_id
        return self


class KnowledgeEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    knowledge_id: str
    knowledge_type: str
    event_type: str
    source_run_id: Optional[str] = None
    source_review_report_id: Optional[str] = None
    details_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class KnowledgePromotionResult(BaseModel):
    promoted_count: int = 0
    demoted_count: int = 0
    archived_count: int = 0
    promoted_knowledge_ids: List[str] = Field(default_factory=list)
    demoted_knowledge_ids: List[str] = Field(default_factory=list)
    archived_knowledge_ids: List[str] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)


class KnowledgeAnalyticsWindow(BaseModel):
    window_type: Literal['all_time', 'reviews', 'days'] = 'all_time'
    window_value: int | None = Field(default=None, ge=1)
    view_mode: Literal['active', 'lineage'] = 'active'

    @model_validator(mode='after')
    def validate_window_value(self) -> 'KnowledgeAnalyticsWindow':
        if self.window_type in {'reviews', 'days'} and self.window_value is None:
            raise ValueError('window_value is required when window_type is reviews or days')
        return self


class KnowledgeAggregatedNode(BaseModel):
    knowledge_id: str
    knowledge_type: KnowledgeTier
    status: KnowledgeStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class KnowledgePruningSignal(BaseModel):
    triggered: bool = False
    threshold: float | int | str | None = None
    actual_value: float | int | str | None = None
    note: str = ''


class KnowledgePruningExplanation(BaseModel):
    low_coverage_recent_window: KnowledgePruningSignal = Field(default_factory=KnowledgePruningSignal)
    high_conflict_recent_window: KnowledgePruningSignal = Field(default_factory=KnowledgePruningSignal)
    low_return_recent_window: KnowledgePruningSignal = Field(default_factory=KnowledgePruningSignal)
    high_failure_recent_window: KnowledgePruningSignal = Field(default_factory=KnowledgePruningSignal)
    regime_drift_detected: KnowledgePruningSignal = Field(default_factory=KnowledgePruningSignal)
    summary: str = ''


class KnowledgeCoverageOut(BaseModel):
    knowledge_id: str
    lineage_id: str
    tier: KnowledgeTier
    status: KnowledgeStatus
    text: str
    category: str
    applicable_event_tags: List[str] = Field(default_factory=list)
    applicable_technical_tags: List[str] = Field(default_factory=list)
    applicable_market_regimes: List[str] = Field(default_factory=list)
    negative_match_tags: List[str] = Field(default_factory=list)
    coverage_count: int = 0
    match_count: int = 0
    evaluated_match_count: int = 0
    hit_count: int = 0
    fail_count: int = 0
    hit_rate: float = 0.0
    fail_rate: float = 0.0
    avg_return_after_match: float = 0.0
    avg_max_drawdown: float = 0.0
    conflict_count: int = 0
    promoted_count: int = 0
    demoted_count: int = 0
    regime_drift_flag: bool = False
    observed_market_regimes: List[str] = Field(default_factory=list)
    is_current_active: bool = False
    aggregated_from_nodes: List[KnowledgeAggregatedNode] = Field(default_factory=list)
    pruning_recommendation: Literal['keep', 'watch', 'deprecate', 'archive_candidate'] = 'keep'
    pruning_reason: str = 'stable_recent_window'
    pruning_explanation: KnowledgePruningExplanation = Field(default_factory=KnowledgePruningExplanation)


class KnowledgeCoverageAggregateOut(BaseModel):
    dimension: str
    key: str
    knowledge_count: int = 0
    knowledge_ids: List[str] = Field(default_factory=list)
    coverage_count: int = 0
    match_count: int = 0
    evaluated_match_count: int = 0
    hit_count: int = 0
    fail_count: int = 0
    hit_rate: float = 0.0
    fail_rate: float = 0.0
    avg_return_after_match: float = 0.0
    avg_max_drawdown: float = 0.0
    conflict_count: int = 0
    promoted_count: int = 0
    demoted_count: int = 0


class KnowledgeCoverageSummaryOut(BaseModel):
    total_knowledge_count: int = 0
    lineage_node_count: int = 0
    active_knowledge_count: int = 0
    active_hot_knowledge_count: int = 0
    active_cold_knowledge_count: int = 0
    pruning_candidate_count: int = 0
    top_conflict_knowledge: List[Dict[str, Any]] = Field(default_factory=list)
    top_low_coverage_knowledge: List[Dict[str, Any]] = Field(default_factory=list)


class KnowledgeCoverageReportOut(BaseModel):
    window: KnowledgeAnalyticsWindow = Field(default_factory=KnowledgeAnalyticsWindow)
    summary: KnowledgeCoverageSummaryOut = Field(default_factory=KnowledgeCoverageSummaryOut)
    items: List[KnowledgeCoverageOut] = Field(default_factory=list)
    by_category: List[KnowledgeCoverageAggregateOut] = Field(default_factory=list)
    by_applicable_event_tag: List[KnowledgeCoverageAggregateOut] = Field(default_factory=list)
    by_applicable_technical_tag: List[KnowledgeCoverageAggregateOut] = Field(default_factory=list)
    by_applicable_market_regime: List[KnowledgeCoverageAggregateOut] = Field(default_factory=list)


class KnowledgePruningCandidateOut(BaseModel):
    knowledge_id: str
    lineage_id: str
    tier: KnowledgeTier
    status: KnowledgeStatus
    category: str
    recommendation: Literal['keep', 'watch', 'deprecate', 'archive_candidate']
    reason: str = 'stable_recent_window'
    reasons: List[str] = Field(default_factory=list)
    trend_signal: Literal['improving', 'stable', 'deteriorating'] = 'stable'
    explanation: KnowledgePruningExplanation = Field(default_factory=KnowledgePruningExplanation)
    coverage_count: int = 0
    match_count: int = 0
    evaluated_match_count: int = 0
    hit_rate: float = 0.0
    fail_rate: float = 0.0
    avg_return_after_match: float = 0.0
    avg_max_drawdown: float = 0.0
    conflict_count: int = 0
    promoted_count: int = 0
    demoted_count: int = 0
    regime_drift_flag: bool = False
    observed_market_regimes: List[str] = Field(default_factory=list)
    is_current_active: bool = False
    aggregated_from_nodes: List[KnowledgeAggregatedNode] = Field(default_factory=list)


class KnowledgePruningReportOut(BaseModel):
    window: KnowledgeAnalyticsWindow = Field(default_factory=KnowledgeAnalyticsWindow)
    total_candidates: int = 0
    items: List[KnowledgePruningCandidateOut] = Field(default_factory=list)


class KnowledgeTrendPoint(BaseModel):
    window_label: str
    coverage_count: int = 0
    match_count: int = 0
    hit_rate: float = 0.0
    fail_rate: float = 0.0
    avg_return_after_match: float = 0.0
    avg_max_drawdown: float = 0.0
    conflict_count: int = 0
    pruning_reason_snapshot: str = 'stable_recent_window'


class KnowledgeTrendSeries(BaseModel):
    knowledge_id: str
    lineage_id: str
    tier: KnowledgeTier
    status: KnowledgeStatus
    category: str
    view_mode: Literal['active', 'lineage'] = 'active'
    trend_windows: List[str] = Field(default_factory=list)
    trend_signal: Literal['improving', 'stable', 'deteriorating'] = 'stable'
    is_current_active: bool = False
    aggregated_from_nodes: List[KnowledgeAggregatedNode] = Field(default_factory=list)
    points: List[KnowledgeTrendPoint] = Field(default_factory=list)


class KnowledgeTrendSummary(BaseModel):
    view_mode: Literal['active', 'lineage'] = 'active'
    trend_windows: List[str] = Field(default_factory=list)
    active_knowledge_count_trend: List[Dict[str, Any]] = Field(default_factory=list)
    pruning_candidate_count_trend: List[Dict[str, Any]] = Field(default_factory=list)
    avg_hit_rate_trend: List[Dict[str, Any]] = Field(default_factory=list)
    avg_conflict_rate_trend: List[Dict[str, Any]] = Field(default_factory=list)


class KnowledgeTrendReportOut(BaseModel):
    view_mode: Literal['active', 'lineage'] = 'active'
    summary: KnowledgeTrendSummary = Field(default_factory=KnowledgeTrendSummary)
    items: List[KnowledgeTrendSeries] = Field(default_factory=list)


class KnowledgeTimelineEvent(BaseModel):
    event_id: str
    event_type: str
    knowledge_id: str
    knowledge_type: KnowledgeTier
    lineage_id: str
    source_run_id: Optional[str] = None
    source_review_report_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    details_json: Dict[str, Any] = Field(default_factory=dict)
    before_status: KnowledgeStatus | None = None
    after_status: KnowledgeStatus | None = None
    metrics_snapshot: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeTimelineSummary(BaseModel):
    total_nodes: int = 0
    total_events: int = 0
    promoted_count: int = 0
    demoted_count: int = 0
    archived_count: int = 0
    current_status: KnowledgeStatus | None = None


class KnowledgeTimelineOut(BaseModel):
    lineage_id: str
    current_active_node: KnowledgeAggregatedNode | None = None
    lineage_summary: KnowledgeTimelineSummary = Field(default_factory=KnowledgeTimelineSummary)
    events: List[KnowledgeTimelineEvent] = Field(default_factory=list)


class KnowledgeLifecycleSummary(BaseModel):
    lineage_id: str
    category: str = ''
    applicable_market_regimes: List[str] = Field(default_factory=list)
    knowledge_type: KnowledgeTier | None = None
    current_status: KnowledgeStatus | None = None
    current_active_node: KnowledgeAggregatedNode | None = None
    first_created_at: Optional[datetime] = None
    first_promoted_at: Optional[datetime] = None
    first_demoted_at: Optional[datetime] = None
    last_archived_at: Optional[datetime] = None
    lifecycle_days: float | None = None
    promotion_to_demotion_days: float | None = None
    restore_to_next_degrade_days: float | None = None
    promotion_count: int = 0
    demotion_count: int = 0
    degrade_count: int = 0
    restore_count: int = 0
    archive_count: int = 0
    status_flip_count: int = 0
    lifecycle_state: Literal['young', 'stable', 'fragile', 'oscillating', 'retired'] = 'young'
    total_nodes: int = 0
    total_events: int = 0


class KnowledgeLifecycleAggregateSummary(BaseModel):
    dimension: str
    key: str
    lineage_count: int = 0
    avg_lifecycle_days: float = 0.0
    avg_promotion_to_demotion_days: float = 0.0
    avg_status_flip_count: float = 0.0
    archive_rate: float = 0.0
    oscillating_rate: float = 0.0


class KnowledgeLifecycleReportOut(BaseModel):
    total_lineages: int = 0
    items: List[KnowledgeLifecycleSummary] = Field(default_factory=list)
    by_category: List[KnowledgeLifecycleAggregateSummary] = Field(default_factory=list)
    by_applicable_market_regime: List[KnowledgeLifecycleAggregateSummary] = Field(default_factory=list)
    by_knowledge_type: List[KnowledgeLifecycleAggregateSummary] = Field(default_factory=list)


class KnowledgeCoverageItem(KnowledgeCoverageOut):
    pass


class KnowledgePruningCandidate(KnowledgePruningCandidateOut):
    pass


class FlowState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    run_id: str
    flow_type: FlowType
    as_of_date: date
    prompt_version: str
    agent_version: str
    feature_set_version: str
    model_version: str
    status: RunStatus = RunStatus.PENDING
    current_node: str = ''
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    watchlist_symbols: List[str] = Field(default_factory=list)
    news_articles: List[Dict[str, Any]] = Field(default_factory=list)
    historical_briefs: List[Dict[str, Any]] = Field(default_factory=list)
    daily_brief: Optional[str] = None
    market_snapshots: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    indicator_snapshots: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    evidence_pack: List[EvidenceRef] = Field(default_factory=list)
    candidates: List[CandidateOut] = Field(default_factory=list)
    agent_messages: List[Dict[str, Any]] = Field(default_factory=list)
    agent_results: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    recommendations: List[CandidateOut] = Field(default_factory=list)
    prediction_artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    trade_ocr: Optional[TradeOCRResult] = None
    user_confirmation: Optional[bool] = None
    review_verdict: Optional[ReviewVerdict] = None
    knowledge_items: List[KnowledgeItem] = Field(default_factory=list)


class MLExperimentRequest(BaseModel):
    as_of_date: date
    symbols: List[str] = Field(default_factory=list)
    dataset_version: str = 'dataset-v1'
    feature_set_version: str = 'feature-set-v1'
    taxonomy_version: str = 'taxonomy-v1'
    tag_encoder_version: str = 'tag-encoder-v1'
    model_name: str = 'sklearn_random_forest'
    label_horizon: int = 5
    cv_method: str = 'time_series_split'
    extra_params: Dict[str, Any] = Field(default_factory=dict)


class MLExperimentRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    experiment_id: str
    experiment_group_id: str
    experiment_mode: str
    dataset_version: str
    feature_set_version: str
    taxonomy_version: str
    tag_encoder_version: str
    model_name: str
    label_horizon: int
    cv_method: str
    artifact_path: str = ''
    metrics_json: Dict[str, Any] = Field(default_factory=dict)
    params_json: Dict[str, Any] = Field(default_factory=dict)
    shap_summary_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MLExperimentResponse(BaseModel):
    experiment_id: str
    dataset_version: str
    feature_set_version: str
    taxonomy_version: str
    tag_encoder_version: str
    model_name: str
    label_horizon: int
    cv_method: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
    baseline_metrics: Dict[str, Any] = Field(default_factory=dict)
    hybrid_metrics: Dict[str, Any] = Field(default_factory=dict)
    experiment_records: List[MLExperimentRecordOut] = Field(default_factory=list)
    top_taxonomy_feature_importances: List[Dict[str, Any]] = Field(default_factory=list)
    artifact_path: str = ''
    shap_summary: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
