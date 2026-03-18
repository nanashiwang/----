def show_backtest(sqlite_client, tushare_api):
    st.header("回测系统")

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("结束日期", datetime.now())

    hold_days = st.slider("持有天数", 1, 20, 5)

    if st.button("运行回测", type="primary"):
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
