from __future__ import annotations

try:
    import shap
except Exception:  # pragma: no cover - optional runtime dependency
    shap = None


class ExplainabilityService:
    def compute(self, model_bundle, dataset: list[dict], label_column: str = 'target_return') -> dict:
        if not dataset:
            return {'available': False, 'reason': 'empty dataset'}

        feature_means = {
            feature: sum(float(row.get(feature, 0.0) or 0.0) for row in dataset) / len(dataset)
            for feature in model_bundle.feature_columns
        }
        fallback_importance = self._fallback_importance(model_bundle, dataset, label_column)

        if shap is None or model_bundle.model_name == 'stub_mean_model':
            return self._build_summary(
                available=False,
                feature_means=feature_means,
                importance_summary=fallback_importance,
                reason='shap unavailable' if shap is None else 'stub model',
            )

        try:  # pragma: no cover - requires SHAP runtime compatibility
            data_matrix = [[float(row.get(feature, 0.0) or 0.0) for feature in model_bundle.feature_columns] for row in dataset]
            explainer = shap.Explainer(model_bundle.model, data_matrix)
            shap_values = explainer(data_matrix)
            importance_summary = {
                feature: float(abs(shap_values.values[:, idx]).mean())
                for idx, feature in enumerate(model_bundle.feature_columns)
            }
            return self._build_summary(
                available=True,
                feature_means=feature_means,
                importance_summary=importance_summary,
            )
        except Exception as exc:
            return self._build_summary(
                available=False,
                feature_means=feature_means,
                importance_summary=fallback_importance,
                reason=str(exc),
            )

    def _build_summary(
        self,
        *,
        available: bool,
        feature_means: dict[str, float],
        importance_summary: dict[str, float],
        reason: str | None = None,
    ) -> dict:
        sorted_items = sorted(importance_summary.items(), key=lambda item: item[1], reverse=True)
        taxonomy_items = [item for item in sorted_items if ':' in item[0]]
        payload = {
            'available': available,
            'feature_means': feature_means,
            'importance_summary': importance_summary,
            'top_features': [
                {'feature': feature, 'importance': importance}
                for feature, importance in sorted_items[:10]
            ],
            'top_taxonomy_features': [
                {'feature': feature, 'importance': importance}
                for feature, importance in taxonomy_items[:10]
            ],
        }
        if available:
            payload['shap_importance'] = importance_summary
        if reason:
            payload['reason'] = reason
        return payload

    @staticmethod
    def _fallback_importance(model_bundle, dataset: list[dict], label_column: str) -> dict[str, float]:
        if not dataset:
            return {}
        targets = [float(row.get(label_column, 0.0) or 0.0) for row in dataset]
        target_mean = sum(targets) / len(targets)
        summary: dict[str, float] = {}
        for feature in model_bundle.feature_columns:
            values = [float(row.get(feature, 0.0) or 0.0) for row in dataset]
            feature_mean = sum(values) / len(values)
            covariance = sum((value - feature_mean) * (target - target_mean) for value, target in zip(values, targets))
            summary[feature] = abs(covariance) / max(len(values), 1)
        return summary
