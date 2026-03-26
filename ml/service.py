from __future__ import annotations

from core.ids import generate_prefixed_id
from core.time import utcnow
from domain.schemas import MLExperimentRecordOut, MLExperimentRequest, MLExperimentResponse
from domain.taxonomy import TAXONOMY_VERSION
from ml.dataset_builder import DatasetBuilder
from ml.datasets.tag_encoder import TAG_ENCODER_VERSION
from ml.experiment_tracker import ExperimentTracker
from ml.explainability import ExplainabilityService
from ml.feature_builder import FeatureBuilder
from ml.predictor import Predictor
from ml.trainer import ModelTrainer


class MLExperimentService:
    def __init__(
        self,
        feature_snapshot_repository,
        daily_brief_repository,
        ml_experiment_repository,
        tracking_uri: str,
    ):
        self.dataset_builder = DatasetBuilder(feature_snapshot_repository, daily_brief_repository)
        self.feature_builder = FeatureBuilder()
        self.trainer = ModelTrainer()
        self.predictor = Predictor()
        self.tracker = ExperimentTracker(tracking_uri)
        self.explainer = ExplainabilityService()
        self.ml_experiment_repository = ml_experiment_repository

    def run(self, payload: MLExperimentRequest) -> MLExperimentResponse:
        dataset_result = self.dataset_builder.build(payload.as_of_date, payload.symbols or None)
        dataset = dataset_result.rows
        experiment_group_id = generate_prefixed_id('ml')
        taxonomy_version = payload.taxonomy_version or dataset_result.taxonomy_version or TAXONOMY_VERSION
        tag_encoder_version = payload.tag_encoder_version or TAG_ENCODER_VERSION

        if not dataset:
            return MLExperimentResponse(
                experiment_id=experiment_group_id,
                dataset_version=payload.dataset_version,
                feature_set_version=payload.feature_set_version,
                taxonomy_version=taxonomy_version,
                tag_encoder_version=tag_encoder_version,
                model_name=payload.model_name,
                label_horizon=payload.label_horizon,
                cv_method=payload.cv_method,
                metrics={'row_count': 0},
            baseline_metrics={'row_count': 0},
            hybrid_metrics={'row_count': 0},
            top_taxonomy_feature_importances=[],
            artifact_path='',
            shap_summary={'available': False, 'reason': 'no dataset'},
            created_at=utcnow(),
        )

        baseline_result = self.feature_builder.build(
            dataset,
            experiment_mode='baseline',
            tag_encoder_version=tag_encoder_version,
        )
        hybrid_result = self.feature_builder.build(
            dataset,
            experiment_mode='hybrid',
            tag_encoder_version=tag_encoder_version,
        )

        baseline_bundle = self.trainer.train(
            dataset=baseline_result.rows,
            feature_columns=baseline_result.feature_columns,
            label_column='target_return',
            model_name=payload.model_name,
            cv_method=payload.cv_method,
            extra_params=payload.extra_params,
            experiment_mode='baseline',
            taxonomy_feature_columns=[],
        )
        hybrid_bundle = self.trainer.train(
            dataset=hybrid_result.rows,
            feature_columns=hybrid_result.feature_columns,
            label_column='target_return',
            model_name=payload.model_name,
            cv_method=payload.cv_method,
            extra_params=payload.extra_params,
            experiment_mode='hybrid',
            taxonomy_feature_columns=hybrid_result.taxonomy_feature_columns,
        )

        baseline_predictions = self.predictor.predict(baseline_bundle, baseline_result.rows)
        hybrid_predictions = self.predictor.predict(hybrid_bundle, hybrid_result.rows)
        baseline_explainability = self.explainer.compute(baseline_bundle, baseline_result.rows)
        hybrid_explainability = self.explainer.compute(hybrid_bundle, hybrid_result.rows)

        comparison_metrics = self._build_comparison_metrics(
            baseline_metrics=baseline_bundle.metrics,
            hybrid_metrics=hybrid_bundle.metrics,
            row_count=len(dataset),
        )
        artifact_path = self.tracker.log(
            experiment_name=experiment_group_id,
            payload={
                'params': {
                    'dataset_version': payload.dataset_version,
                    'feature_set_version': payload.feature_set_version,
                    'taxonomy_version': taxonomy_version,
                    'tag_encoder_version': tag_encoder_version,
                    'label_horizon': payload.label_horizon,
                    'cv_method': payload.cv_method,
                    'model_name': payload.model_name,
                },
                'metrics': {
                    **comparison_metrics,
                    'baseline_prediction_rows': len(baseline_predictions),
                    'hybrid_prediction_rows': len(hybrid_predictions),
                },
                'comparison': {
                    'baseline': baseline_bundle.metrics,
                    'hybrid': hybrid_bundle.metrics,
                },
                'baseline_top_predictions': baseline_predictions[:5],
                'hybrid_top_predictions': hybrid_predictions[:5],
                'tag_sources': dataset_result.tag_sources,
            },
        )

        baseline_record = self.ml_experiment_repository.create(
            experiment_id=generate_prefixed_id('mlexp'),
            experiment_group_id=experiment_group_id,
            experiment_mode='baseline',
            dataset_version=payload.dataset_version,
            feature_set_version=payload.feature_set_version,
            taxonomy_version=taxonomy_version,
            tag_encoder_version=tag_encoder_version,
            model_name=baseline_bundle.model_name,
            label_horizon=payload.label_horizon,
            cv_method=payload.cv_method,
            artifact_path=artifact_path,
            metrics_json=baseline_bundle.metrics,
            params_json={
                'feature_columns': baseline_result.feature_columns,
                'numeric_feature_columns': baseline_result.numeric_feature_columns,
                'taxonomy_feature_columns': baseline_result.taxonomy_feature_columns,
                'tag_sources': dataset_result.tag_sources,
            },
            shap_summary_json=baseline_explainability,
        )
        hybrid_record = self.ml_experiment_repository.create(
            experiment_id=generate_prefixed_id('mlexp'),
            experiment_group_id=experiment_group_id,
            experiment_mode='hybrid',
            dataset_version=payload.dataset_version,
            feature_set_version=payload.feature_set_version,
            taxonomy_version=taxonomy_version,
            tag_encoder_version=tag_encoder_version,
            model_name=hybrid_bundle.model_name,
            label_horizon=payload.label_horizon,
            cv_method=payload.cv_method,
            artifact_path=artifact_path,
            metrics_json=hybrid_bundle.metrics,
            params_json={
                'feature_columns': hybrid_result.feature_columns,
                'numeric_feature_columns': hybrid_result.numeric_feature_columns,
                'taxonomy_feature_columns': hybrid_result.taxonomy_feature_columns,
                'tag_sources': dataset_result.tag_sources,
            },
            shap_summary_json=hybrid_explainability,
        )

        return MLExperimentResponse(
            experiment_id=experiment_group_id,
            dataset_version=payload.dataset_version,
            feature_set_version=payload.feature_set_version,
            taxonomy_version=taxonomy_version,
            tag_encoder_version=tag_encoder_version,
            model_name=payload.model_name,
            label_horizon=payload.label_horizon,
            cv_method=payload.cv_method,
            metrics={
                **comparison_metrics,
                'baseline_top_symbol': baseline_predictions[0]['symbol'] if baseline_predictions else '',
                'hybrid_top_symbol': hybrid_predictions[0]['symbol'] if hybrid_predictions else '',
            },
            baseline_metrics=baseline_bundle.metrics,
            hybrid_metrics=hybrid_bundle.metrics,
            experiment_records=[
                MLExperimentRecordOut.model_validate(baseline_record),
                MLExperimentRecordOut.model_validate(hybrid_record),
            ],
            top_taxonomy_feature_importances=hybrid_explainability.get('top_taxonomy_features', []),
            artifact_path=artifact_path,
            shap_summary=hybrid_explainability,
            created_at=utcnow(),
        )

    @staticmethod
    def _build_comparison_metrics(
        *,
        baseline_metrics: dict[str, float],
        hybrid_metrics: dict[str, float],
        row_count: int,
    ) -> dict[str, float]:
        baseline_mae = float(baseline_metrics.get('mae', 0.0))
        hybrid_mae = float(hybrid_metrics.get('mae', 0.0))
        baseline_r2 = float(baseline_metrics.get('r2', 0.0))
        hybrid_r2 = float(hybrid_metrics.get('r2', 0.0))
        return {
            'row_count': float(row_count),
            'baseline_mae': baseline_mae,
            'hybrid_mae': hybrid_mae,
            'mae_improvement': round(baseline_mae - hybrid_mae, 6),
            'baseline_r2': baseline_r2,
            'hybrid_r2': hybrid_r2,
            'r2_delta': round(hybrid_r2 - baseline_r2, 6),
        }
