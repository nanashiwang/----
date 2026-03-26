from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import mlflow
except Exception:  # pragma: no cover - optional runtime dependency
    mlflow = None


class ExperimentTracker:
    def __init__(self, tracking_uri: str):
        self.tracking_uri = tracking_uri
        if mlflow is not None:
            mlflow.set_tracking_uri(tracking_uri)

    def log(self, experiment_name: str, payload: dict[str, Any]) -> str:
        artifact_path = f'artifacts/{experiment_name}.json'
        if mlflow is None:
            output = Path('artifacts')
            output.mkdir(parents=True, exist_ok=True)
            (output / f'{experiment_name}.json').write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                encoding='utf-8',
            )
            return artifact_path

        with mlflow.start_run(run_name=experiment_name):  # pragma: no cover - requires mlflow runtime
            mlflow.log_params(payload.get('params', {}))
            mlflow.log_metrics(payload.get('metrics', {}))
        return artifact_path
