# 多Agent量化交易系统

基于LangGraph的AI多Agent协作量化交易系统，整合机器学习和大语言模型，实现市场观察、智能推理、交易执行和复盘学习的完整闭环。

## 系统架构

```
观察集群 → 推理集群 → 行动集群 → 复盘集群
   ↓          ↓          ↓          ↓
        数据层 (MongoDB + SQLite)
```

## 核心特性

- **观察层**：自动收集市场事件和技术指标
- **推理层**：多Agent协作筛选候选股票（辩论机制 + 六顶思考帽）
- **行动层**：辅助手动交易，OCR识别交割单
- **复盘层**：基于实际结果更新知识库，持续优化

## 技术栈

- **Agent框架**：LangGraph
- **LLM**：支持OpenAI、Claude、国内模型（自定义API）
- **数据源**：Tushare Pro
- **数据库**：MongoDB（知识库）+ SQLite（结构化数据）
- **语言**：Python 3.12

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入配置：

```bash
cp .env.example .env
```

编辑 `.env`：
```
LLM_API_KEY=your-api-key
TUSHARE_TOKEN=your-tushare-token
```

### 3. 初始化数据库

```bash
python main.py init
```

### 4. 运行工作流

```bash
# 观察工作流
python main.py observe

# 推理工作流
python main.py reason

# 复盘工作流
python main.py review
```

## 项目结构

```
量化交易/
├── src/
│   ├── agents/          # Agent定义
│   ├── workflows/       # LangGraph工作流
│   ├── data/           # 数据层
│   ├── llm/            # LLM适配器
│   ├── knowledge/      # 知识库管理
│   └── utils/          # 工具函数
├── config/             # 配置文件
├── data/               # 数据存储
├── logs/               # 日志
└── main.py            # 主入口
```

## 配置说明

编辑 `config/config.yaml` 自定义配置：

```yaml
llm:
  provider: "openai"  # openai/anthropic/custom
  api_base: "https://api.openai.com/v1"
  model: "gpt-4"

tushare:
  token: "your-token"

database:
  mongodb:
    uri: "mongodb://localhost:27017"
  sqlite:
    path: "data/sqlite/trading.db"
```

## 开发状态

- [x] 基础设施搭建
- [x] 数据库设计
- [x] LLM适配层
- [ ] 观察集群
- [ ] 推理集群
- [ ] 行动集群
- [ ] 复盘集群

## 免责声明

本系统仅供学习研究使用，不构成任何投资建议。股市有风险，投资需谨慎。

## License

MIT
