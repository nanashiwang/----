# Web界面、测试和回测系统使用指南

## 一、Web界面

### 启动方式

**Windows:**
```bash
start_web.bat
```

**Linux/Mac:**
```bash
chmod +x start_web.sh
./start_web.sh
```

**或直接运行:**
```bash
streamlit run web_app.py
```

访问地址：http://localhost:8501

### 功能模块

#### 1. 📊 推荐看板
- 查看每日推荐股票
- 显示推荐权重和理由
- 支持日期筛选

#### 2. 📈 复盘分析
- 查看历史复盘记录
- 成功/失败案例分析
- 关键洞察展示

#### 3. 🧠 知识库
- **热知识库**：显示置信度和测试次数
- **冷知识库**：沉淀的高质量经验

#### 4. 🔬 回测系统
- 设置回测时间范围
- 调整持有天数
- 查看胜率、平均收益等指标
- 可视化收益曲线

#### 5. ⚙️ 工作流
- 一键执行观察/推理/复盘工作流

## 二、测试系统

### 运行测试

```bash
# 运行所有测试
python run_tests.py

# 或使用pytest
pytest tests/ -v

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html
```

### 测试模块

1. **test_sqlite_client.py** - 数据库测试
   - 表创建验证
   - 数据插入/查询

2. **test_knowledge.py** - 知识库测试
   - 经验添加
   - 经验测试机制

3. **test_llm_factory.py** - LLM工厂测试
   - 多提供商支持
   - 错误处理

## 三、回测系统

### 使用方式

**命令行（开发中）:**
```python
from src.backtest.engine import BacktestEngine
from src.data.db.sqlite_client import SQLiteClient
from src.data.sources.tushare_api import TushareAPI

sqlite_client = SQLiteClient("data/sqlite/trading.db")
tushare_api = TushareAPI("your-token")
engine = BacktestEngine(sqlite_client, tushare_api)

result = engine.run_backtest("2024-01-01", "2024-03-19", hold_days=5)
print(f"胜率: {result['win_rate']:.2%}")
print(f"平均收益: {result['avg_return']:.2%}")
```

**Web界面:**
1. 进入"回测系统"标签
2. 选择开始/结束日期
3. 设置持有天数
4. 点击"运行回测"

### 回测指标

- **总交易次数**：推荐股票数量
- **胜率**：盈利交易占比
- **平均收益**：所有交易的平均收益率
- **最大收益**：单笔最高收益率
- **最小收益**：单笔最低收益率

## 四、完整工作流示例

### 日常使用流程

```bash
# 1. 早盘前 - 观察市场
python main.py observe

# 2. 开盘后 - 获取推荐
python main.py reason

# 3. 查看推荐（Web界面）
streamlit run web_app.py
# 访问 http://localhost:8501

# 4. 手动交易（根据推荐）

# 5. 收盘后 - 复盘
python main.py review

# 6. 周末 - 回测验证
# 在Web界面运行回测系统
```

### 自动化调度（可选）

使用cron或Windows任务计划程序：

```bash
# Linux cron示例
# 每个交易日早上8:30观察
30 8 * * 1-5 cd /path/to/project && python main.py observe

# 每个交易日上午9:35推理
35 9 * * 1-5 cd /path/to/project && python main.py reason

# 每个交易日下午15:30复盘
30 15 * * 1-5 cd /path/to/project && python main.py review
```

## 五、故障排查

### Web界面无法启动
- 检查端口8501是否被占用
- 确认streamlit已安装：`pip install streamlit`
- 查看错误日志

### 回测数据不足
- 确认推荐记录已存在
- 检查Tushare数据是否完整
- 调整回测时间范围

### 测试失败
- 检查依赖是否完整安装
- 确认数据库路径正确
- 查看具体错误信息

## 六、性能优化建议

1. **LLM调用优化**
   - 使用缓存减少重复调用
   - 批量处理降低延迟

2. **数据库优化**
   - 定期清理历史数据
   - 添加索引提升查询速度

3. **回测优化**
   - 限制回测范围
   - 使用本地缓存数据

## 七、扩展开发

### 添加新的回测指标

编辑 `src/backtest/engine.py`：

```python
def calculate_sharpe_ratio(self, returns):
    """计算夏普比率"""
    return returns.mean() / returns.std()
```

### 自定义Web页面

编辑 `web_app.py`，添加新的tab：

```python
with tabs[5]:
    show_custom_analysis()
```

### 添加新的测试用例

在 `tests/` 目录创建新文件：

```python
# tests/test_custom.py
import unittest

class TestCustom(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
```
