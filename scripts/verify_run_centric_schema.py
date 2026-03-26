from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import get_settings


EXPECTED_TABLES = {
    "workflow_runs",
    "agent_node_runs",
    "news_articles",
    "daily_briefs",
    "feature_snapshots",
    "prediction_artifacts",
    "recommendations",
    "trades",
    "review_reports",
    "hot_knowledge",
    "cold_knowledge",
    "knowledge_events",
    "ml_experiments",
}


def main() -> int:
    settings = get_settings()
    engine = create_engine(settings.postgres_dsn, future=True)
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    missing_tables = sorted(EXPECTED_TABLES - existing_tables)
    present_tables = sorted(EXPECTED_TABLES & existing_tables)

    print(f"DATABASE_URL={settings.postgres_dsn}")
    print("present_tables:")
    for table_name in present_tables:
        print(f"  - {table_name}")

    if missing_tables:
        print("missing_tables:")
        for table_name in missing_tables:
            print(f"  - {table_name}")
        return 1

    print("schema_check=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
