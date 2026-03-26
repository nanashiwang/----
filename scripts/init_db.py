#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化旧系统仍在使用的 SQLite / MongoDB 基础资源。

注意：
- run-centric 新表不再由这里创建
- workflow_runs / agent_node_runs / daily_briefs / recommendations 等表
  只能通过 Alembic 迁移管理
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.db.mongo_client import MongoDBClient
from src.data.db.sqlite_client import SQLiteClient
from src.utils.config import get_config


def main() -> None:
    config = get_config()

    print("正在初始化旧系统 SQLite 基础表...")
    SQLiteClient(config.database.sqlite.path)
    print(f"OK SQLite 基础表已就绪: {config.database.sqlite.path}")

    print()
    print("正在连接 MongoDB...")
    MongoDBClient(
        config.database.mongodb.uri,
        config.database.mongodb.db_name,
    )
    print(f"OK MongoDB 已连接: {config.database.mongodb.db_name}")

    print()
    print("注意: run-centric 新表请使用 Alembic 创建")
    print("命令: python -m alembic upgrade head")


if __name__ == "__main__":
    main()
