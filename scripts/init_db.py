#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.db.sqlite_client import SQLiteClient
from src.data.db.mongo_client import MongoDBClient
from src.utils.config import get_config


def main():
    config = get_config()

    print("正在初始化SQLite数据库...")
    sqlite_client = SQLiteClient(config.database.sqlite.path)
    print(f"✓ SQLite数据库已创建: {config.database.sqlite.path}")

    print("\n正在连接MongoDB...")
    mongo_client = MongoDBClient(
        config.database.mongodb.uri,
        config.database.mongodb.db_name
    )
    print(f"✓ MongoDB已连接: {config.database.mongodb.db_name}")

    print("\n数据库初始化完成！")


if __name__ == "__main__":
    main()
