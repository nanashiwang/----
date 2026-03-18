#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多Agent量化交易系统 - 主入口
"""
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

import argparse
from datetime import datetime, timedelta
from loguru import logger

from src.utils.config import get_config
from src.data.db.sqlite_client import SQLiteClient
from src.data.db.mongo_client import MongoDBClient
from src.data.sources.tushare_api import TushareAPI
from src.llm.factory import LLMFactory
from src.agents.observe.event_collector import EventCollector
from src.agents.observe.tech_analyst import TechAnalyst
from src.agents.reason.news_screener import NewsScreener
from src.agents.review.retrospect_agent import RetrospectAgent
from src.workflows.observe_flow import create_observe_workflow
from src.workflows.reason_flow import create_reason_workflow
from src.workflows.review_flow import create_review_workflow


def init_system():
    """初始化系统"""
    config = get_config()

    # 配置日志
    logger.add(
        config.logging.file,
        rotation="1 day",
        retention="30 days",
        level=config.logging.level
    )

    # 初始化数据库
    sqlite_client = SQLiteClient(config.database.sqlite.path)
    mongo_client = MongoDBClient(
        config.database.mongodb.uri,
        config.database.mongodb.db_name
    )

    # 初始化LLM
    llm = LLMFactory.create(
        config.llm.provider,
        api_key=config.llm.api_key,
        api_base=config.llm.api_base,
        model=config.llm.model,
        temperature=config.llm.temperature,
        max_tokens=config.llm.max_tokens
    )

    # 初始化Tushare
    tushare_api = TushareAPI(config.tushare.token)

    logger.info("系统初始化完成")
    return config, sqlite_client, mongo_client, llm, tushare_api


def main():
    parser = argparse.ArgumentParser(description="多Agent量化交易系统")
    parser.add_argument("command", choices=["observe", "reason", "review", "init"],
                       help="执行的命令")
    parser.add_argument("--date", type=str, help="指定日期 (YYYY-MM-DD)")

    args = parser.parse_args()

    config, sqlite_client, mongo_client, llm, tushare_api = init_system()

    if args.command == "init":
        logger.info("数据库初始化完成")
        print("✓ 数据库初始化成功")

    elif args.command == "observe":
        logger.info("启动观察工作流...")
        date = args.date or datetime.now().strftime("%Y-%m-%d")

        # 获取新闻数据
        news_df = tushare_api.get_news(
            date.replace("-", ""),
            date.replace("-", "")
        )
        news_data = news_df.to_dict('records') if not news_df.empty else []

        # 获取股票池
        stock_pool = tushare_api.get_stock_basic()['ts_code'].tolist()[:100]

        # 创建工作流
        event_collector = EventCollector(llm, sqlite_client)
        tech_analyst = TechAnalyst(tushare_api, sqlite_client)
        workflow = create_observe_workflow(event_collector, tech_analyst)

        # 执行
        result = workflow.invoke({
            "date": date,
            "news_data": news_data,
            "stock_codes": stock_pool[:10],
            "event_brief": "",
            "tech_data": {}
        })

        print(f"✓ 观察完成: {date}")
        print(f"事件简报: {result['event_brief'][:100]}...")

    elif args.command == "reason":
        logger.info("启动推理工作流...")
        date = args.date or datetime.now().strftime("%Y-%m-%d")

        # 获取今日简报
        with sqlite_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM event_briefs WHERE date = ?", (date,))
            row = cursor.fetchone()
            event_brief = row['content'] if row else "无简报"

        # 获取股票池和技术数据
        stock_pool = tushare_api.get_stock_basic()['ts_code'].tolist()[:100]
        tech_data = {}

        # 创建工作流
        screener = NewsScreener(llm)
        workflow = create_reason_workflow(screener, llm, sqlite_client)

        # 执行
        result = workflow.invoke({
            "event_brief": event_brief,
            "stock_pool": stock_pool,
            "tech_data": tech_data,
            "candidates": [],
            "debate_results": {},
            "final_picks": []
        })

        print(f"✓ 推理完成: {date}")
        print(f"推荐股票: {len(result['final_picks'])}只")
        for pick in result['final_picks']:
            print(f"  {pick['ts_code']}: 权重{pick['weight']:.2f} - {pick['reason'][:50]}")

    elif args.command == "review":
        logger.info("启动复盘工作流...")
        date = args.date or (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # 创建工作流
        retrospect_agent = RetrospectAgent(llm, sqlite_client, mongo_client, tushare_api)
        workflow = create_review_workflow(retrospect_agent)

        # 执行
        result = workflow.invoke({"date": date, "review_result": {}})

        print(f"✓ 复盘完成: {date}")
        print(f"总推荐: {result['review_result']['total']}只")
        print(f"成功: {result['review_result']['correct']}只")
        print(f"失败: {result['review_result']['wrong']}只")


if __name__ == "__main__":
    main()
