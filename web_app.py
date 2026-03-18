import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timedelta
import pandas as pd
from src.utils.config import get_config
from src.data.db.sqlite_client import SQLiteClient
from src.data.db.mongo_client import MongoDBClient
from src.data.sources.tushare_api import TushareAPI
from src.llm.factory import LLMFactory
from src.backtest.engine import BacktestEngine

st.set_page_config(page_title="多Agent量化交易系统", layout="wide")

@st.cache_resource
def init_system():
    config = get_config()
    sqlite_client = SQLiteClient(config.database.sqlite.path)
    mongo_client = MongoDBClient(config.database.mongodb.uri, config.database.mongodb.db_name)
    llm = LLMFactory.create(
        config.llm.provider,
        api_key=config.llm.api_key,
        api_base=config.llm.api_base,
        model=config.llm.model
    )
    tushare_api = TushareAPI(config.tushare.token)
    return sqlite_client, mongo_client, llm, tushare_api

def main():
    st.title("🤖 多Agent量化交易系统")

    sqlite_client, mongo_client, llm, tushare_api = init_system()

    tabs = st.tabs(["📊 推荐看板", "📈 复盘分析", "🧠 知识库", "🔬 回测系统", "⚙️ 工作流"])

    with tabs[0]:
        show_recommendations(sqlite_client)

    with tabs[1]:
        show_reviews(sqlite_client, mongo_client)

    with tabs[2]:
        show_knowledge_base(mongo_client)

    with tabs[3]:
        show_backtest(sqlite_client, tushare_api)

    with tabs[4]:
        run_workflows(sqlite_client, mongo_client, llm, tushare_api)

def show_recommendations(sqlite_client):
    st.header("今日推荐")

    date = st.date_input("选择日期", datetime.now())
    date_str = date.strftime("%Y-%m-%d")

    with sqlite_client.get_connection() as conn:
        df = pd.read_sql(
            "SELECT * FROM recommendations WHERE date = ? ORDER BY weight DESC",
            conn, params=(date_str,)
        )

    if df.empty:
        st.info("暂无推荐数据")
    else:
        st.dataframe(df[['ts_code', 'weight', 'reason', 'created_at']], use_container_width=True)

def show_reviews(sqlite_client, mongo_client):
    st.header("复盘分析")

    briefs = list(mongo_client.get_collection("review_briefs").find().sort("date", -1).limit(10))

    if not briefs:
        st.info("暂无复盘数据")
    else:
        for brief in briefs:
            with st.expander(f"{brief['date'].strftime('%Y-%m-%d')} - {brief['summary']}"):
                st.write(f"**成功**: {', '.join(brief['correct_predictions'])}")
                st.write(f"**失败**: {', '.join(brief['wrong_predictions'])}")
                st.write("**关键洞察**:")
                for insight in brief['key_insights']:
                    st.write(f"- {insight}")

def show_knowledge_base(mongo_client):
    st.header("知识库")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("热知识库")
        hot_kb = list(mongo_client.get_collection("hot_knowledge").find().sort("confidence", -1).limit(10))
        for kb in hot_kb:
            st.metric(
                kb['content'][:50],
                f"{kb['confidence']:.1%}",
                f"测试{kb['test_count']}次"
            )

    with col2:
        st.subheader("冷知识库")
        cold_kb = list(mongo_client.get_collection("cold_knowledge_tech_analyst").find().limit(10))
        for kb in cold_kb:
            st.write(f"- {kb['content']}")

def run_workflows(sqlite_client, mongo_client, llm, tushare_api):
    st.header("执行工作流")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔍 观察工作流", use_container_width=True):
            with st.spinner("执行中..."):
                st.info("观察工作流执行中，请稍候...")

    with col2:
        if st.button("🧠 推理工作流", use_container_width=True):
            with st.spinner("执行中..."):
                st.info("推理工作流执行中，请稍候...")

    with col3:
        if st.button("📝 复盘工作流", use_container_width=True):
            with st.spinner("执行中..."):
                st.info("复盘工作流执行中，请稍候...")

def show_backtest(sqlite_client, tushare_api):
    st.header("回测系统")

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("结束日期", datetime.now())

    hold_days = st.slider("持有天数", 1, 20, 5)

    if st.button("运行回测", type="primary"):
        from src.backtest.engine import BacktestEngine
        engine = BacktestEngine(sqlite_client, tushare_api)

        with st.spinner("回测中..."):
            result = engine.run_backtest(
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                hold_days
            )

        if "error" in result:
            st.error(result["error"])
        else:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("总交易次数", result["total_trades"])
            col2.metric("胜率", f"{result['win_rate']:.1%}")
            col3.metric("平均收益", f"{result['avg_return']:.2%}")
            col4.metric("最大收益", f"{result['max_return']:.2%}")

            st.subheader("详细结果")
            df = pd.DataFrame(result["details"])
            st.dataframe(df, use_container_width=True)

            st.line_chart(df.set_index('date')['return_rate'])

if __name__ == "__main__":
    main()
