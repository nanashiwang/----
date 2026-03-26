from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from apps.api.app import create_app
from core.enums import FlowType, KnowledgeStatus, RecommendationAction, RunStatus
from core.ids import generate_prefixed_id
from infrastructure.repositories import KnowledgeAnalyticsRepository
from memory.analytics import KnowledgeAnalyticsService
from tests.architecture.helpers import build_test_harness


def _create_workflow_run(harness, run_id: str, flow_type: FlowType, as_of_date: date) -> None:
    harness.deps.workflow_runs.create(
        run_id=run_id,
        flow_type=flow_type,
        status=RunStatus.COMPLETED,
        as_of_date=as_of_date,
        trigger_source='test',
        idempotency_key=None,
        prompt_version='prompt-v1',
        agent_version='agent-v1',
        feature_set_version='feature-set-v1',
        model_version='model-v1',
        input_json={},
        output_json={},
        metadata_json={},
        error_json={},
    )


def _build_analytics_service(harness) -> KnowledgeAnalyticsService:
    return KnowledgeAnalyticsService(
        analytics_repository=KnowledgeAnalyticsRepository(harness.session_manager),
        knowledge_repository=harness.deps.knowledge_repository,
    )


def _create_hot_knowledge(
    harness,
    *,
    text: str,
    category: str,
    applicable_event_tags: list[str] | None = None,
    applicable_technical_tags: list[str] | None = None,
    applicable_market_regimes: list[str] | None = None,
    negative_match_tags: list[str] | None = None,
):
    run_id = generate_prefixed_id('review')
    _create_workflow_run(harness, run_id, FlowType.REVIEW, date(2026, 3, 26))
    return harness.deps.knowledge_repository.create_hot_knowledge(
        {
            'text': text,
            'category': category,
            'source_run_ids': [run_id],
            'source_recommendation_ids': [],
            'tests_survived': 3,
            'pass_count': 2,
            'fail_count': 1,
            'pass_rate': 0.6667,
            'status': 'active',
            'applicable_event_tags': applicable_event_tags or [],
            'applicable_technical_tags': applicable_technical_tags or [],
            'applicable_market_regimes': applicable_market_regimes or [],
            'negative_match_tags': negative_match_tags or [],
            'evidence_json': {},
        },
        source_run_id=run_id,
    )


def _create_cold_knowledge(
    harness,
    *,
    text: str,
    category: str,
    applicable_event_tags: list[str] | None = None,
    applicable_technical_tags: list[str] | None = None,
    applicable_market_regimes: list[str] | None = None,
    negative_match_tags: list[str] | None = None,
):
    promotion_run_id = generate_prefixed_id('review')
    _create_workflow_run(harness, promotion_run_id, FlowType.REVIEW, date(2026, 3, 26))
    hot = harness.deps.knowledge_repository.create_hot_knowledge(
        {
            'text': text,
            'category': category,
            'source_run_ids': [promotion_run_id],
            'source_recommendation_ids': ['rec_seed'],
            'tests_survived': 12,
            'pass_count': 9,
            'fail_count': 3,
            'pass_rate': 0.75,
            'status': 'active',
            'applicable_event_tags': applicable_event_tags or [],
            'applicable_technical_tags': applicable_technical_tags or [],
            'applicable_market_regimes': applicable_market_regimes or [],
            'negative_match_tags': negative_match_tags or [],
            'evidence_json': {},
        },
        source_run_id=promotion_run_id,
    )
    return harness.deps.knowledge_repository.promote_to_cold(
        knowledge_id=hot.knowledge_id,
        promotion_reason='analytics seed',
        promotion_run_id=promotion_run_id,
    )


def _create_matched_recommendation_and_review(
    harness,
    *,
    knowledge_id: str,
    verdict: str,
    conflict: bool,
    actual_return_5d: float,
    benchmark_return: float,
    max_drawdown: float,
    market_regime_tags: list[str] | None = None,
    reason_date: date = date(2026, 3, 25),
    review_date: date = date(2026, 3, 26),
):
    reason_run_id = generate_prefixed_id('reason')
    review_run_id = generate_prefixed_id('review')
    _create_workflow_run(harness, reason_run_id, FlowType.REASON, reason_date)
    _create_workflow_run(harness, review_run_id, FlowType.REVIEW, review_date)

    evidence_json = {
        'knowledge_refs': [
            {
                'ref_id': knowledge_id,
                'ref_type': 'cold_knowledge',
                'title': 'analytics seed',
                'source': 'cold_knowledge',
            }
        ],
        'knowledge_impact_json': [
            {
                'knowledge_id': knowledge_id,
                'impact_type': 'risk_penalty' if conflict else 'support',
                'impact_score': 0.08 if conflict else 0.05,
                'reason': 'analytics test seed',
                'matched_tags': ['event_type:sector_rotation'],
                'conflicting_tags': ['risk_pattern:event_conflict_risk'] if conflict else [],
                'match_score': 0.7,
            }
        ],
        'knowledge_conflict_flag': conflict,
        'normalized_event_tags': ['event_type:sector_rotation', 'event_direction:bullish'],
        'technical_pattern_tags': ['trend_state:short_term_uptrend', 'momentum_state:momentum_balanced'],
        'risk_pattern_tags': ['risk_pattern:event_conflict_risk'] if conflict else [],
        'market_regime_tags': market_regime_tags or ['market_regime:benchmark_uptrend'],
        'evidence_refs': [
            {
                'ref_id': 'article:test',
                'ref_type': 'news_article',
                'title': 'test',
                'source': 'test',
            }
        ],
    }
    recommendation = harness.deps.recommendation_repository.bulk_create(
        [
            {
                'run_id': reason_run_id,
                'prediction_artifact_id': None,
                'symbol': '000001.SZ',
                'action': RecommendationAction.INCLUDE,
                'weight': 0.6,
                'final_score': 0.6,
                'reason': 'analytics test',
                'risk_flags_json': {
                    'risk_flags': ['knowledge_conflict'] if conflict else [],
                    'knowledge_conflict_flag': conflict,
                },
                'evidence_json': evidence_json,
            }
        ]
    )[0]

    harness.deps.review_repository.create(
        run_id=review_run_id,
        target_run_id=reason_run_id,
        as_of_date=review_date,
        horizon=5,
        summary_text='analytics review',
        verdicts_json={
            'items': [
                {
                    'recommendation_id': recommendation.recommendation_id,
                    'symbol': '000001.SZ',
                    'expected_action': 'include',
                    'actual_return_1d': actual_return_5d / 3,
                    'actual_return_3d': actual_return_5d / 2,
                    'actual_return_5d': actual_return_5d,
                    'benchmark_return': benchmark_return,
                    'max_drawdown': max_drawdown,
                    'verdict': verdict,
                    'key_success_factors': [],
                    'key_failure_factors': [],
                    'evidence_json': evidence_json,
                    'error_json': {},
                }
            ]
        },
        metrics_json={},
        knowledge_json={},
    )
    return recommendation


def _seed_review_series(
    harness,
    *,
    knowledge_id: str,
    review_dates: list[date],
    verdicts: list[str],
    conflicts: list[bool],
    returns: list[float],
    benchmarks: list[float] | None = None,
    drawdowns: list[float] | None = None,
):
    benchmarks = benchmarks or [0.0 for _ in review_dates]
    drawdowns = drawdowns or [-0.02 for _ in review_dates]
    for index, review_date in enumerate(review_dates):
        _create_matched_recommendation_and_review(
            harness,
            knowledge_id=knowledge_id,
            verdict=verdicts[index],
            conflict=conflicts[index],
            actual_return_5d=returns[index],
            benchmark_return=benchmarks[index],
            max_drawdown=drawdowns[index],
            review_date=review_date,
            reason_date=review_date - timedelta(days=1),
        )


def test_knowledge_coverage_aggregates_match_fail_and_conflict(harness):
    analytics_service = _build_analytics_service(harness)
    cold = _create_cold_knowledge(
        harness,
        text='Conflicting uptrend setup needs deprecation.',
        category='review_failure_rule',
        applicable_event_tags=['event_type:sector_rotation', 'event_direction:bullish'],
        applicable_technical_tags=['trend_state:short_term_uptrend'],
        applicable_market_regimes=['market_regime:benchmark_uptrend'],
        negative_match_tags=['risk_pattern:event_conflict_risk'],
    )
    _create_matched_recommendation_and_review(
        harness,
        knowledge_id=cold.knowledge_id,
        verdict='underperform',
        conflict=True,
        actual_return_5d=-0.04,
        benchmark_return=0.01,
        max_drawdown=-0.09,
    )

    item = analytics_service.get_knowledge_coverage(cold.knowledge_id)

    assert item is not None
    assert item.coverage_count >= 1
    assert item.match_count == 1
    assert item.evaluated_match_count == 1
    assert item.fail_count == 1
    assert item.conflict_count == 1
    assert item.fail_rate == 1.0


def test_pruning_rules_return_watch_deprecate_and_archive_candidate(harness):
    analytics_service = _build_analytics_service(harness)

    _create_hot_knowledge(
        harness,
        text='Low coverage hot knowledge should stay under watch.',
        category='review_success_rule',
        applicable_event_tags=['event_type:policy_support'],
        applicable_market_regimes=['market_regime:benchmark_uptrend'],
    )
    deprecate_cold = _create_cold_knowledge(
        harness,
        text='High conflict cold knowledge should be deprecated.',
        category='review_failure_rule',
        applicable_event_tags=['event_type:sector_rotation', 'event_direction:bullish'],
        applicable_technical_tags=['trend_state:short_term_uptrend'],
        applicable_market_regimes=['market_regime:benchmark_uptrend'],
        negative_match_tags=['risk_pattern:event_conflict_risk'],
    )
    _create_matched_recommendation_and_review(
        harness,
        knowledge_id=deprecate_cold.knowledge_id,
        verdict='underperform',
        conflict=True,
        actual_return_5d=-0.05,
        benchmark_return=0.02,
        max_drawdown=-0.1,
        market_regime_tags=['market_regime:benchmark_downtrend'],
    )
    _create_matched_recommendation_and_review(
        harness,
        knowledge_id=deprecate_cold.knowledge_id,
        verdict='outperform',
        conflict=False,
        actual_return_5d=0.01,
        benchmark_return=0.0,
        max_drawdown=-0.03,
        market_regime_tags=['market_regime:benchmark_downtrend'],
    )
    archive_cold = _create_cold_knowledge(
        harness,
        text='Demoted cold knowledge with zero coverage should be archived later.',
        category='review_failure_rule',
        applicable_event_tags=['event_type:risk_warning'],
        applicable_market_regimes=['market_regime:high_volatility'],
    )
    demotion_run_id = generate_prefixed_id('review')
    _create_workflow_run(harness, demotion_run_id, FlowType.REVIEW, date(2026, 3, 27))
    harness.deps.knowledge_repository.demote_cold_knowledge(
        knowledge_id=archive_cold.knowledge_id,
        reason='analytics archive seed',
        source_run_id=demotion_run_id,
        archive=False,
    )

    report = analytics_service.list_pruning_candidates()
    pruning_map = {item.knowledge_id: item for item in report.items}

    watch_items = [item for item in report.items if item.recommendation == 'watch']

    assert watch_items
    assert pruning_map[deprecate_cold.knowledge_id].recommendation == 'deprecate'
    assert pruning_map[archive_cold.knowledge_id].recommendation == 'archive_candidate'


def test_knowledge_analytics_api_returns_empty_payloads_without_data(harness, monkeypatch):
    analytics_service = _build_analytics_service(harness)

    monkeypatch.setattr('apps.api.routes.knowledge.get_knowledge_analytics_service', lambda: analytics_service)
    client = TestClient(create_app())

    coverage_response = client.get('/api/knowledge/coverage?window_type=reviews&window_value=5&view_mode=active')
    pruning_response = client.get('/api/knowledge/pruning-candidates?window_type=days&window_value=7&view_mode=lineage')

    assert coverage_response.status_code == 200
    assert coverage_response.json()['data']['summary']['total_knowledge_count'] == 0
    assert coverage_response.json()['data']['items'] == []

    assert pruning_response.status_code == 200
    assert pruning_response.json()['data']['total_candidates'] == 0
    assert pruning_response.json()['data']['items'] == []


def test_knowledge_analytics_api_rejects_invalid_window_type(harness, monkeypatch):
    analytics_service = _build_analytics_service(harness)

    monkeypatch.setattr('apps.api.routes.knowledge.get_knowledge_analytics_service', lambda: analytics_service)
    client = TestClient(create_app())

    response = client.get('/api/knowledge/coverage?window_type=invalid&view_mode=active')

    assert response.status_code == 422
    assert response.json()['success'] is False


def test_knowledge_analytics_api_requires_window_value_for_review_window(harness, monkeypatch):
    analytics_service = _build_analytics_service(harness)

    monkeypatch.setattr('apps.api.routes.knowledge.get_knowledge_analytics_service', lambda: analytics_service)
    client = TestClient(create_app())

    response = client.get('/api/knowledge/coverage?window_type=reviews&view_mode=active')

    assert response.status_code == 422
    assert response.json()['success'] is False


def test_all_time_window_allows_empty_window_value(harness):
    analytics_service = _build_analytics_service(harness)

    report = analytics_service.build_coverage_report(window_type='all_time', window_value=None, view_mode='active')

    assert report.summary.total_knowledge_count == 0


def test_reviews_window_limits_recent_review_stats(harness):
    analytics_service = _build_analytics_service(harness)
    cold = _create_cold_knowledge(
        harness,
        text='Recent review window should only keep latest review.',
        category='review_failure_rule',
        applicable_event_tags=['event_type:sector_rotation', 'event_direction:bullish'],
        applicable_technical_tags=['trend_state:short_term_uptrend'],
        applicable_market_regimes=['market_regime:benchmark_uptrend'],
    )
    _create_matched_recommendation_and_review(
        harness,
        knowledge_id=cold.knowledge_id,
        verdict='underperform',
        conflict=True,
        actual_return_5d=-0.04,
        benchmark_return=0.01,
        max_drawdown=-0.08,
        review_date=date(2026, 3, 24),
    )
    _create_matched_recommendation_and_review(
        harness,
        knowledge_id=cold.knowledge_id,
        verdict='outperform',
        conflict=False,
        actual_return_5d=0.03,
        benchmark_return=0.0,
        max_drawdown=-0.02,
        review_date=date(2026, 3, 26),
    )

    item = analytics_service.get_knowledge_coverage(
        cold.knowledge_id,
        window_type='reviews',
        window_value=1,
        view_mode='active',
    )

    assert item is not None
    assert item.match_count == 1
    assert item.hit_rate == 1.0
    assert item.pruning_explanation.high_conflict_recent_window.triggered is False


def test_days_window_limits_recent_day_stats(harness):
    analytics_service = _build_analytics_service(harness)
    cold = _create_cold_knowledge(
        harness,
        text='Recent day window should exclude stale review days.',
        category='review_failure_rule',
        applicable_event_tags=['event_type:sector_rotation', 'event_direction:bullish'],
        applicable_technical_tags=['trend_state:short_term_uptrend'],
        applicable_market_regimes=['market_regime:benchmark_uptrend'],
    )
    _create_matched_recommendation_and_review(
        harness,
        knowledge_id=cold.knowledge_id,
        verdict='underperform',
        conflict=True,
        actual_return_5d=-0.03,
        benchmark_return=0.01,
        max_drawdown=-0.07,
        review_date=date(2026, 3, 20),
    )
    _create_matched_recommendation_and_review(
        harness,
        knowledge_id=cold.knowledge_id,
        verdict='outperform',
        conflict=False,
        actual_return_5d=0.02,
        benchmark_return=0.0,
        max_drawdown=-0.02,
        review_date=date(2026, 3, 26),
    )

    item = analytics_service.get_knowledge_coverage(
        cold.knowledge_id,
        window_type='days',
        window_value=3,
        view_mode='active',
    )

    assert item is not None
    assert item.match_count == 1
    assert item.fail_rate == 0.0
    assert item.pruning_explanation.low_coverage_recent_window.triggered is True


def test_lineage_view_returns_historical_lineage_nodes(harness):
    analytics_service = _build_analytics_service(harness)
    cold = _create_cold_knowledge(
        harness,
        text='Lineage view should keep hot and cold history.',
        category='review_success_rule',
        applicable_event_tags=['event_type:sector_rotation'],
        applicable_market_regimes=['market_regime:benchmark_uptrend'],
    )

    report = analytics_service.build_coverage_report(view_mode='lineage')
    lineage_nodes = [item for item in report.items if item.lineage_id == cold.lineage_id]

    assert len(lineage_nodes) >= 2
    assert all(len(item.aggregated_from_nodes) == 1 for item in lineage_nodes)
    assert all(item.aggregated_from_nodes[0].knowledge_id == item.knowledge_id for item in lineage_nodes)


def test_active_view_dedupes_lineage_and_keeps_current_node(harness):
    analytics_service = _build_analytics_service(harness)
    cold = _create_cold_knowledge(
        harness,
        text='Active view should collapse lineage duplicates.',
        category='review_success_rule',
        applicable_event_tags=['event_type:sector_rotation'],
        applicable_market_regimes=['market_regime:benchmark_uptrend'],
    )

    report = analytics_service.build_coverage_report(view_mode='active')
    item = next(
        entry
        for entry in report.items
        if any(node.knowledge_id == cold.knowledge_id for node in entry.aggregated_from_nodes)
    )
    resolved_from_hot = analytics_service.get_knowledge_coverage(
        cold.source_hot_knowledge_id,
        view_mode='active',
    )
    cold_node_ids = [node.knowledge_id for node in item.aggregated_from_nodes]

    assert item.knowledge_id == cold.knowledge_id
    assert item.lineage_id == cold.lineage_id
    assert len(item.aggregated_from_nodes) >= 2
    assert cold.knowledge_id in cold_node_ids
    assert item.is_current_active is True
    assert resolved_from_hot is not None
    assert resolved_from_hot.knowledge_id == cold.knowledge_id


def test_pruning_explanation_changes_after_windowing(harness):
    analytics_service = _build_analytics_service(harness)
    cold = _create_cold_knowledge(
        harness,
        text='Windowed pruning should be less pessimistic when recent review improves.',
        category='review_failure_rule',
        applicable_event_tags=['event_type:sector_rotation', 'event_direction:bullish'],
        applicable_technical_tags=['trend_state:short_term_uptrend'],
        applicable_market_regimes=['market_regime:benchmark_uptrend'],
        negative_match_tags=['risk_pattern:event_conflict_risk'],
    )
    _create_matched_recommendation_and_review(
        harness,
        knowledge_id=cold.knowledge_id,
        verdict='underperform',
        conflict=True,
        actual_return_5d=-0.06,
        benchmark_return=0.01,
        max_drawdown=-0.09,
        review_date=date(2026, 3, 24),
    )
    _create_matched_recommendation_and_review(
        harness,
        knowledge_id=cold.knowledge_id,
        verdict='outperform',
        conflict=False,
        actual_return_5d=0.05,
        benchmark_return=0.0,
        max_drawdown=-0.02,
        review_date=date(2026, 3, 26),
    )

    all_time_item = analytics_service.get_knowledge_coverage(cold.knowledge_id, view_mode='active')
    recent_item = analytics_service.get_knowledge_coverage(
        cold.knowledge_id,
        window_type='reviews',
        window_value=1,
        view_mode='active',
    )

    assert all_time_item is not None and recent_item is not None
    assert all_time_item.pruning_recommendation == 'watch'
    assert all_time_item.pruning_explanation.high_conflict_recent_window.triggered is True
    assert recent_item.pruning_recommendation == 'watch'
    assert recent_item.pruning_explanation.high_conflict_recent_window.triggered is False
    assert recent_item.pruning_explanation.low_coverage_recent_window.triggered is True
    assert recent_item.pruning_reason == 'low_coverage'


def test_knowledge_trends_support_last_5_10_20_review_windows(harness):
    analytics_service = _build_analytics_service(harness)
    cold = _create_cold_knowledge(
        harness,
        text='Trend windows should retain comparable review snapshots.',
        category='review_success_rule',
        applicable_event_tags=['event_type:sector_rotation'],
        applicable_technical_tags=['trend_state:short_term_uptrend'],
        applicable_market_regimes=['market_regime:benchmark_uptrend'],
    )
    review_dates = [date(2026, 3, 7) + timedelta(days=index) for index in range(20)]
    verdicts = ['underperform'] * 10 + ['outperform'] * 10
    conflicts = [True] * 10 + [False] * 10
    returns = [-0.03] * 10 + [0.04] * 10
    _seed_review_series(
        harness,
        knowledge_id=cold.knowledge_id,
        review_dates=review_dates,
        verdicts=verdicts,
        conflicts=conflicts,
        returns=returns,
    )

    series = analytics_service.get_knowledge_trends(
        knowledge_id=cold.knowledge_id,
        view_mode='active',
    )

    assert series is not None
    assert series.trend_windows == ['last_5_reviews', 'last_10_reviews', 'last_20_reviews']
    point_map = {point.window_label: point for point in series.points}
    assert point_map['last_5_reviews'].match_count == 5
    assert point_map['last_10_reviews'].hit_rate == 1.0
    assert point_map['last_20_reviews'].fail_rate == 0.5


def test_knowledge_trends_active_view_and_lineage_view_have_different_node_counts(harness):
    analytics_service = _build_analytics_service(harness)
    cold = _create_cold_knowledge(
        harness,
        text='Trend view should collapse lineage in active mode.',
        category='review_success_rule',
        applicable_event_tags=['event_type:sector_rotation'],
        applicable_market_regimes=['market_regime:benchmark_uptrend'],
    )

    active_report = analytics_service.build_coverage_trends(view_mode='active')
    lineage_report = analytics_service.build_coverage_trends(view_mode='lineage')

    active_items = [item for item in active_report.items if item.lineage_id == cold.lineage_id]
    lineage_items = [item for item in lineage_report.items if item.lineage_id == cold.lineage_id]

    assert len(active_items) == 1
    assert len(lineage_items) >= 2


def test_trend_signal_detects_improving_and_deteriorating_knowledge():
    improving_harness = build_test_harness()
    improving_service = _build_analytics_service(improving_harness)
    improving = _create_cold_knowledge(
        improving_harness,
        text='Improving knowledge should be identified.',
        category='review_success_rule',
        applicable_event_tags=['event_type:sector_rotation'],
        applicable_market_regimes=['market_regime:benchmark_uptrend'],
    )
    review_dates = [date(2026, 3, 7) + timedelta(days=index) for index in range(20)]
    _seed_review_series(
        improving_harness,
        knowledge_id=improving.knowledge_id,
        review_dates=review_dates,
        verdicts=['underperform'] * 10 + ['outperform'] * 10,
        conflicts=[True] * 10 + [False] * 10,
        returns=[-0.03] * 10 + [0.05] * 10,
    )
    improving_series = improving_service.get_knowledge_trends(knowledge_id=improving.knowledge_id, view_mode='active')

    deteriorating_harness = build_test_harness()
    deteriorating_service = _build_analytics_service(deteriorating_harness)
    deteriorating = _create_cold_knowledge(
        deteriorating_harness,
        text='Deteriorating knowledge should be identified.',
        category='review_failure_rule',
        applicable_event_tags=['event_type:risk_warning'],
        applicable_market_regimes=['market_regime:benchmark_downtrend'],
    )
    _seed_review_series(
        deteriorating_harness,
        knowledge_id=deteriorating.knowledge_id,
        review_dates=review_dates,
        verdicts=['outperform'] * 10 + ['underperform'] * 10,
        conflicts=[False] * 10 + [True] * 10,
        returns=[0.05] * 10 + [-0.04] * 10,
    )
    deteriorating_series = deteriorating_service.get_knowledge_trends(
        knowledge_id=deteriorating.knowledge_id,
        view_mode='active',
    )
    pruning_report = deteriorating_service.list_pruning_candidates(view_mode='active')
    pruning_map = {item.knowledge_id: item for item in pruning_report.items}

    assert improving_series is not None and deteriorating_series is not None
    assert improving_series.trend_signal == 'improving'
    assert deteriorating_series.trend_signal == 'deteriorating'
    assert pruning_map[deteriorating.knowledge_id].trend_signal == 'deteriorating'


def test_trend_endpoints_return_empty_series_without_data(harness, monkeypatch):
    analytics_service = _build_analytics_service(harness)

    monkeypatch.setattr('apps.api.routes.knowledge.get_knowledge_analytics_service', lambda: analytics_service)
    client = TestClient(create_app())

    coverage_response = client.get('/api/knowledge/coverage/trends?view_mode=active')
    pruning_response = client.get('/api/knowledge/pruning/trends?view_mode=lineage')

    assert coverage_response.status_code == 200
    assert coverage_response.json()['data']['items'] == []
    assert pruning_response.status_code == 200
    assert pruning_response.json()['data']['items'] == []
