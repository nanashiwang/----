@echo off
REM 启动Web界面 (Windows)

echo 启动多Agent量化交易系统Web界面...
streamlit run web_app.py --server.port 8501
