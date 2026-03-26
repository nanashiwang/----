from __future__ import annotations

from datetime import date

from core.enums import FlowType
from domain.schemas import MLExperimentRequest, WorkflowTriggerIn
from infrastructure.repositories import MLExperimentRepository
from ml.dataset_builder import DatasetBuilder
from ml.datasets.tag_encoder import TAG_ENCODER_VERSION, TagFeatureEncoder
from ml.service import MLExperimentService
from workflows.service import WorkflowApplicationService


def _prepare_observe(harness, trade_date: date = date(2026, 3, 25)):
    workflow_service = WorkflowApplicationService(lambda: harness.deps)
    workflow_service.trigger_workflow(
        WorkflowTriggerIn(flow_type=FlowType.OBSERVE, as_of_date=trade_date),
        async_mode=False,
    )


def _build_ml_service(harness) -> tuple[MLExperimentService, MLExperimentRepository]:
    repository = MLExperimentRepository(harness.session_manager)
    service = MLExperimentService(
        feature_snapshot_repository=harness.deps.feature_snapshot_repository,
        daily_brief_repository=harness.deps.daily_brief_repository,
        ml_experiment_repository=repository,
        tracking_uri='file:./mlruns-tests',
    )
    return service, repository


def test_dataset_builder_reads_normalized_taxonomy_tags(harness):
    _prepare_observe(harness)
    builder = DatasetBuilder(
        feature_snapshot_repository=harness.deps.feature_snapshot_repository,
        daily_brief_repository=harness.deps.daily_brief_repository,
    )

    result = builder.build(date(2026, 3, 25))

    assert result.rows
    first_row = result.rows[0]
    assert first_row['normalized_event_tags']
    assert first_row['technical_pattern_tags']
    assert first_row['market_regime_tags']
    assert result.taxonomy_version == 'taxonomy-v1'


def test_tag_encoder_outputs_stable_multi_hot_features():
    encoder = TagFeatureEncoder()
    dataset = [
        {
            'symbol': '000001.SZ',
            'normalized_event_tags': ['event_type:sector_rotation', 'event_direction:bullish'],
            'technical_pattern_tags': ['trend_state:short_term_uptrend'],
            'risk_pattern_tags': ['risk_pattern:high_volatility_risk'],
            'market_regime_tags': ['market_regime:benchmark_uptrend'],
            'sentiment_state_tags': ['sentiment_state:risk_on'],
            'breadth_state_tags': ['breadth_state:breadth_strong'],
        },
        {
            'symbol': '600519.SH',
            'normalized_event_tags': ['event_direction:bullish'],
            'technical_pattern_tags': ['trend_state:short_term_downtrend'],
            'risk_pattern_tags': [],
            'market_regime_tags': ['market_regime:benchmark_downtrend'],
            'sentiment_state_tags': ['sentiment_state:risk_off'],
            'breadth_state_tags': ['breadth_state:breadth_weak'],
        },
    ]

    vocabulary = encoder.fit(dataset)
    encoded = encoder.transform(dataset, vocabulary=vocabulary)

    assert vocabulary == sorted(vocabulary)
    assert 'event_type:sector_rotation' in encoded.feature_columns
    assert encoded.rows[0]['event_type:sector_rotation'] == 1.0
    assert encoded.rows[1]['event_type:sector_rotation'] == 0.0
    assert encoded.rows[0]['tag_count:normalized_event_tags'] == 2.0


def test_taxonomy_versions_are_written_to_training_records(harness):
    _prepare_observe(harness)
    service, repository = _build_ml_service(harness)

    response = service.run(
        MLExperimentRequest(
            as_of_date=date(2026, 3, 25),
            dataset_version='dataset-taxonomy-v1',
            feature_set_version='feature-hybrid-v1',
            taxonomy_version='taxonomy-v1',
            tag_encoder_version=TAG_ENCODER_VERSION,
        )
    )
    records = repository.list_by_group(response.experiment_id)

    assert len(records) == 2
    assert all(record.taxonomy_version == 'taxonomy-v1' for record in records)
    assert all(record.tag_encoder_version == TAG_ENCODER_VERSION for record in records)
    assert {record.experiment_mode for record in records} == {'baseline', 'hybrid'}


def test_baseline_and_hybrid_training_both_complete(harness):
    _prepare_observe(harness)
    service, _ = _build_ml_service(harness)

    response = service.run(
        MLExperimentRequest(
            as_of_date=date(2026, 3, 25),
            dataset_version='dataset-taxonomy-v1',
            feature_set_version='feature-hybrid-v1',
        )
    )

    assert response.baseline_metrics['row_count'] >= 1
    assert response.hybrid_metrics['row_count'] >= 1
    assert len(response.experiment_records) == 2
    assert 'baseline_mae' in response.metrics
    assert 'hybrid_mae' in response.metrics


def test_explainability_contains_readable_taxonomy_feature_names(harness):
    _prepare_observe(harness)
    service, _ = _build_ml_service(harness)

    response = service.run(
        MLExperimentRequest(
            as_of_date=date(2026, 3, 25),
            dataset_version='dataset-taxonomy-v1',
            feature_set_version='feature-hybrid-v1',
        )
    )

    top_features = response.top_taxonomy_feature_importances

    assert top_features
    assert any(':' in item['feature'] for item in top_features)
