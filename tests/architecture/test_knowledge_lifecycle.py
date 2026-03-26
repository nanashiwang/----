from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from core.enums import KnowledgeStatus
from core.ids import generate_prefixed_id
from infrastructure.db.postgres.models import HotKnowledgeORM, KnowledgeEventORM
from tests.architecture.test_knowledge_analytics import _build_analytics_service, _create_cold_knowledge
from tests.architecture.test_knowledge_timeline import _seed_lineage_timeline


def _shift_lineage_event_days(harness, lineage_id: str, offsets_by_event_type: dict[str, list[int]]) -> None:
    lineage_nodes = harness.deps.knowledge_repository.list_lineage_nodes(lineage_id)['all']
    knowledge_ids = [node.knowledge_id for node in lineage_nodes]
    with harness.session_manager.session_scope() as session:
        rows = list(
            session.execute(
                select(KnowledgeEventORM)
                .where(KnowledgeEventORM.knowledge_id.in_(knowledge_ids))
                .order_by(KnowledgeEventORM.created_at.asc(), KnowledgeEventORM.event_id.asc())
            ).scalars().all()
        )
        counters = {key: 0 for key in offsets_by_event_type}
        baseline = min((row.created_at for row in rows if row.created_at is not None), default=None)
        if baseline is None:
            return
        for row in rows:
            event_type = row.event_type
            offsets = offsets_by_event_type.get(event_type)
            if not offsets:
                continue
            index = min(counters[event_type], len(offsets) - 1)
            row.created_at = baseline + timedelta(days=offsets[index])
            row.updated_at = row.created_at
            counters[event_type] += 1
            session.add(row)


def _seed_stable_lineage(harness, *, category: str = 'lifecycle_category') -> str:
    cold = _create_cold_knowledge(
        harness,
        text='Stable lifecycle knowledge should keep a long active window.',
        category=category,
        applicable_event_tags=['event_type:sector_rotation'],
        applicable_market_regimes=['market_regime:benchmark_uptrend'],
    )
    _shift_lineage_event_days(
        harness,
        cold.lineage_id,
        {
            'hot_created': [0],
            'promoted_to_cold': [8],
            'promoted_from_hot': [8],
        },
    )
    return cold.lineage_id


def _seed_retired_lineage(harness, *, category: str = 'lifecycle_category') -> str:
    cold = _create_cold_knowledge(
        harness,
        text='Retired lifecycle knowledge should end in archived status.',
        category=category,
        applicable_event_tags=['event_type:risk_warning'],
        applicable_market_regimes=['market_regime:benchmark_downtrend'],
    )
    harness.deps.knowledge_repository.demote_cold_knowledge(
        knowledge_id=cold.knowledge_id,
        reason='retire lineage',
        source_run_id=None,
        archive=True,
    )
    _shift_lineage_event_days(
        harness,
        cold.lineage_id,
        {
            'hot_created': [0],
            'promoted_to_cold': [3],
            'promoted_from_hot': [3],
            'archived_from_cold': [12],
            'archived_after_cold_failure': [12],
        },
    )
    return cold.lineage_id


def test_single_lineage_lifecycle_summary_is_calculated_correctly(harness):
    analytics_service, cold = _seed_lineage_timeline(harness)
    _shift_lineage_event_days(
        harness,
        cold.lineage_id,
        {
            'hot_created': [0],
            'promoted_to_cold': [5],
            'promoted_from_hot': [5],
            'demoted_to_hot': [15],
            'restored_from_cold': [15],
            'archived_hot': [20],
        },
    )

    summary = analytics_service.get_lineage_lifecycle_summary(lineage_id=cold.lineage_id)

    assert summary is not None
    assert summary.lineage_id == cold.lineage_id
    assert summary.lifecycle_days == 20.0
    assert summary.promotion_to_demotion_days == 10.0
    assert summary.status_flip_count >= 4
    assert summary.archive_count >= 1


def test_lifecycle_state_rules_cover_oscillating_stable_and_retired(harness):
    analytics_service = _build_analytics_service(harness)
    _, oscillating_cold = _seed_lineage_timeline(harness)
    stable_lineage_id = _seed_stable_lineage(harness, category='stable_category')
    retired_lineage_id = _seed_retired_lineage(harness, category='retired_category')

    oscillating_summary = analytics_service.get_lineage_lifecycle_summary(lineage_id=oscillating_cold.lineage_id)
    stable_summary = analytics_service.get_lineage_lifecycle_summary(lineage_id=stable_lineage_id)
    retired_summary = analytics_service.get_lineage_lifecycle_summary(lineage_id=retired_lineage_id)

    assert oscillating_summary is not None and oscillating_summary.lifecycle_state == 'oscillating'
    assert stable_summary is not None and stable_summary.lifecycle_state == 'stable'
    assert retired_summary is not None and retired_summary.lifecycle_state == 'retired'


def test_category_lifecycle_aggregate_summary_is_correct(harness):
    analytics_service = _build_analytics_service(harness)
    first_lineage_id = _seed_stable_lineage(harness, category='aggregate_category')
    second_lineage_id = _seed_retired_lineage(harness, category='aggregate_category')
    _seed_stable_lineage(harness, category='other_category')

    report = analytics_service.build_lifecycle_report(category='aggregate_category')

    by_category = {item.key: item for item in report.by_category}

    assert report.total_lineages == 2
    assert first_lineage_id in {item.lineage_id for item in report.items}
    assert second_lineage_id in {item.lineage_id for item in report.items}
    assert 'aggregate_category' in by_category
    assert by_category['aggregate_category'].lineage_count == 2
    assert by_category['aggregate_category'].avg_lifecycle_days >= 0.0
    assert by_category['aggregate_category'].archive_rate == 0.5


def test_lifecycle_summary_returns_empty_metrics_when_lineage_has_no_events(harness):
    analytics_service = _build_analytics_service(harness)
    lineage_id = generate_prefixed_id('knowledge')
    knowledge_id = generate_prefixed_id('knowledge')

    with harness.session_manager.session_scope() as session:
        row = HotKnowledgeORM(
            knowledge_id=knowledge_id,
            lineage_id=lineage_id,
            text='Manual lineage without timeline events.',
            category='empty_lineage',
            source_run_ids=[],
            source_recommendation_ids=[],
            tests_survived=0,
            pass_count=0,
            fail_count=0,
            pass_rate=0.0,
            applicable_event_tags=[],
            applicable_technical_tags=[],
            applicable_market_regimes=[],
            negative_match_tags=[],
            status=KnowledgeStatus.ACTIVE,
            evidence_json={},
        )
        session.add(row)

    summary = analytics_service.get_lineage_lifecycle_summary(lineage_id=lineage_id)

    assert summary is not None
    assert summary.total_events == 0
    assert summary.first_created_at is None
    assert summary.lifecycle_days is None
    assert summary.promotion_to_demotion_days is None
    assert summary.status_flip_count == 0
    assert summary.lifecycle_state == 'young'
