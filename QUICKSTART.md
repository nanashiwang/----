# 快速开始指南

## 1. 环境准备

### 安装依赖
```bash
cd "D:\code_python\量化交易"
pip install -r requirements.txt
```

### 配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入以下信息：
# LLM_API_KEY=your-openai-or-claude-api-key
# TUSHARE_TOKEN=your-tushare-pro-token
```

### 配置LLM（可选）
编辑 `config/config.yaml` 自定义LLM配置：
```yaml
llm:
  provider: "openai"  # 或 "anthropic" 或 "custom"
  api_base: "https://api.openai.com/v1"  # 自定义API地址
  model: "gpt-4"
```

## 2. 初始化数据库

```bash
python main.py init
```

## 3. 运行工作流

### 观察工作流（每日早盘前运行）
```bash
# 使用今天日期
python main.py observe

# 指定日期
python main.py observe --date 2024-03-19
```

**功能**：
- 收集市场事件和新闻
- 生成每日简报
- 分析技术指标

### 推理工作流（盘中运行）
```bash
python main.py reason
```

**功能**：
- 基于事件简报筛选候选股票
- 多Agent辩论（辩护者vs批评者）
- 六顶思考帽深度分析
- 输出推荐股票和权重

### 复盘工作流（收盘后运行）
```bash
# 复盘昨天的推荐
python main.py review

# 指定日期
python main.py review --date 2024-03-18
```

**功能**：
- 对比推荐与实际表现
- 提取经验教训
- 更新知识库

## 4. 典型使用流程

### 每日工作流
```bash
# 早上9:00前 - 观察市场
python main.py observe

# 上午9:30-10:00 - 获取推荐
python main.py reason

# 手动交易（根据推荐）

# 晚上收盘后 - 复盘
python main.py review
```

## 5. 数据查看

### SQLite数据库
```bash
sqlite3 data/sqlite/trading.db

# 查看推荐记录
SELECT * FROM recommendations ORDER BY date DESC LIMIT 10;

# 查看事件简报
SELECT * FROM event_briefs ORDER BY date DESC LIMIT 5;
```

### MongoDB知识库
```bash
mongosh
use quant_trading

# 查看热知识库
db.hot_knowledge.find().sort({confidence: -1}).limit(10)

# 查看复盘简报
db.review_briefs.find().sort({date: -1}).limit(5)
```

## 6. 注意事项

⚠️ **重要提示**：
- 本系统仅供学习研究，不构成投资建议
- 推荐结果需人工审核后再决策
- 建议先用小资金测试
- 定期检查知识库质量

## 7. 故障排查

### LLM调用失败
- 检查API密钥是否正确
- 检查网络连接
- 查看 `logs/app.log` 日志

### Tushare数据获取失败
- 确认Token有效
- 检查积分是否充足
- 避免频繁调用（有限流）

### MongoDB连接失败
- 确认MongoDB服务已启动
- 检查连接URI配置

## 8. 进阶配置

### 自定义股票池
编辑 `main.py` 中的 `stock_pool` 变量，指定关注的股票列表。

### 调整Agent参数
修改各Agent的Prompt模板，优化分析逻辑。

### 知识库管理
定期审查热知识库，手动沉淀高质量经验到冷知识库。
