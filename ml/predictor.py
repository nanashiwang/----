from __future__ import annotations


class Predictor:
    def predict(self, model_bundle, dataset: list[dict]) -> list[dict]:
        if not dataset:
            return []

        if hasattr(model_bundle.model, 'predict') and model_bundle.model_name != 'stub_mean_model':
            X = [[float(row.get(column, 0.0) or 0.0) for column in model_bundle.feature_columns] for row in dataset]
            raw_predictions = list(model_bundle.model.predict(X))
        else:
            raw_predictions = model_bundle.model.predict(dataset, model_bundle.feature_columns)

        records = []
        for row, prediction in zip(dataset, raw_predictions):
            item = dict(row)
            item['prediction'] = float(prediction)
            records.append(item)
        return sorted(records, key=lambda item: item['prediction'], reverse=True)
