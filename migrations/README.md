# Alembic 迁移说明

当前项目原有数据库初始化方式为：

- `scripts/init_db.py`
- `src/data/db/sqlite_client.py` 中的 `CREATE TABLE IF NOT EXISTS`

这套方式仍可兼容旧 SQLite 功能，但新的 run-centric 架构已经正式接入 Alembic，
后续 `workflow_runs`、`agent_node_runs`、`daily_briefs` 等核心表统一通过迁移管理。

## 默认数据库选择

Alembic 优先读取以下环境变量：

1. `DATABASE_URL`
2. `POSTGRES_DSN`

如果都没有配置，则回退到：

```text
sqlite+pysqlite:///./data/sqlite/run_centric.db
```

## 常用命令

```bash
python -m alembic upgrade head
python -m alembic downgrade -1
python -m alembic current
python -m alembic history
```

## 本地开发推荐

1. 复制 `.env.example` 为 `.env`
2. 保持：

```text
DATABASE_URL=sqlite+pysqlite:///./data/sqlite/run_centric.db
AUTO_INIT_SCHEMA=false
```

3. 执行迁移：

```bash
python -m alembic upgrade head
```

## PostgreSQL 生产示例

```text
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/quant_trading
AUTO_INIT_SCHEMA=false
```

然后执行：

```bash
python -m alembic upgrade head
```

## 表结构验证

可以使用以下脚本检查 9 张 run-centric 表是否已创建：

```bash
python scripts/verify_run_centric_schema.py
```
