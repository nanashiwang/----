from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from apps.api.app import create_app
from core.enums import FlowType
from core.ids import generate_prefixed_id
from tests.architecture.test_knowledge_analytics import (
    _build_analytics_service,
    _create_cold_knowledge,
    _create_matched_recommendation_and_review,
    _create_workflow_run,
)


def _seed_lineage_timeline(harness):
    analytics_service = _build_analytics_service(harness)
    cold = _create_cold_knowledge(
        harness,
        text='Timeline audit trail should stay queryable across lineage transitions.',
        category='timeline_rule',
        applicable_event_tags=['event_type:sector_rotation'],
        applicable_technical_tags=['trend_state:short_term_uptrend'],
        applicable_market_regimes=['market_regime:benchmark_uptrend', 'market_regime:controlled_volatility'],
    )
    _create_matched_recommendation_and_review(
        harness,
        knowledge_id=cold.knowledge_id,
        verdict='outperform',
        conflict=False,
        actual_return_5d=0.04,
        benchmark_return=0.01,
        max_drawdown=-0.02,
        reason_date=date(2026, 3, 25),
        review_date=date(2026, 3, 26),
    )

    demote_run_id = generate_prefixed_id('review')
    _create_workflow_run(harness, demote_run_id, FlowType.REVIEW, date(2026, 3, 27))
    harness.deps.knowledge_repository.demote_cold_knowledge(
        knowledge_id=cold.knowledge_id,
        reason='timeline demotion seed',
        source_run_id=demote_run_id,
        archive=False,
    )
    harness.deps.knowledge_repository.archive(
        cold.source_hot_knowledge_id,
        reason='timeline archive seed',
    )
    return analytics_service, cold


def test_knowledge_id_returns_complete_lineage_timeline(harness):
    analytics_service, cold = _seed_lineage_timeline(harness)

    timeline = analytics_service.get_knowledge_timeline(knowledge_id=cold.knowledge_id)

    assert timeline is not None
    assert timeline.lineage_id == cold.lineage_id
    assert timeline.lineage_summary.total_nodes >= 2
    event_types = [event.event_type for event in timeline.events]
    assert 'created' in event_types
    assert 'promoted' in event_types
    assert 'matched' in event_types
    assert 'reviewed' in event_types


def test_lineage_id_returns_complete_timeline(harness):
    analytics_service, cold = _seed_lineage_timeline(harness)

    timeline = analytics_service.get_lineage_timeline(lineage_id=cold.lineage_id)

    assert timeline is not None
    assert timeline.lineage_id == cold.lineage_id
    assert any(event.knowledge_id == cold.knowledge_id for event in timeline.events)
    assert any(event.knowledge_id == cold.source_hot_knowledge_id for event in timeline.events)


def test_timeline_events_are_sorted_for_promote_demote_archive(harness):
    analytics_service, cold = _seed_lineage_timeline(harness)

    timeline = analytics_service.get_lineage_timeline(lineage_id=cold.lineage_id)

    assert timeline is not None
    event_types = [event.event_type for event in timeline.events]
    assert event_types.index('promoted') < event_types.index('demoted') < event_types.index('archived')


def test_timeline_api_returns_standard_error_when_knowledge_or_lineage_missing(harness, monkeypatch):
    analytics_service = _build_analytics_service(harness)
    monkeypatch.setattr('apps.api.routes.knowledge.get_knowledge_analytics_service', lambda: analytics_service)
    client = TestClient(create_app())

    knowledge_response = client.get('/api/knowledge/knowledge_missing/timeline')
    lineage_response = client.get('/api/knowledge/lineages/lineage_missing/timeline')

    assert knowledge_response.status_code == 404
    assert knowledge_response.json()['success'] is False
    assert lineage_response.status_code == 404
    assert lineage_response.json()['success'] is False


def test_timeline_summary_fields_are_correct(harness):
    analytics_service, cold = _seed_lineage_timeline(harness)

    timeline = analytics_service.get_lineage_timeline(lineage_id=cold.lineage_id)

    assert timeline is not None
    assert timeline.current_active_node is not None
    assert timeline.current_active_node.knowledge_id == cold.knowledge_id
    assert timeline.current_active_node.status.value == 'degraded'
    assert timeline.lineage_summary.total_nodes >= 2
    assert timeline.lineage_summary.total_events == len(timeline.events)
    assert timeline.lineage_summary.promoted_count >= 2
    assert timeline.lineage_summary.demoted_count >= 1
    assert timeline.lineage_summary.archived_count >= 1
    assert timeline.lineage_summary.current_status.value == 'degraded'
