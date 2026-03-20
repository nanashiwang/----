# Docker 使用说明

## 目标

项目已经补齐以下 Docker 资产：

- `Dockerfile`：构建可运行的应用镜像，默认启动 FastAPI 后端并托管前端静态资源
- `docker-compose.yml`：本地一键拉起应用和 MongoDB
- `.github/workflows/docker-publish.yml`：推送到 GitHub 后自动发布 GHCR 镜像

## 1. 本地构建镜像

```bash
docker build -t quant-trading:local .
```

## 2. 本地使用 Compose 启动

先准备环境变量：

```bash
cp .env.example .env
```

然后启动：

```bash
docker compose up -d --build
```

启动后访问：

```text
http://localhost:8000
```

停止服务：

```bash
docker compose down
```

如果还要一起删除 MongoDB 卷：

```bash
docker compose down -v
```

## 3. 直接拉取 GHCR 镜像

当仓库推送到默认分支或打 `v*` 标签后，GitHub Actions 会自动发布镜像到：

```text
ghcr.io/<你的 GitHub 用户名>/quant-trading:latest
```

拉取命令：

```bash
docker pull ghcr.io/<你的 GitHub 用户名>/quant-trading:latest
```

## 4. 使用 Compose 直接拉取并运行

项目已提供 `docker-compose.pull.yml`，默认直接拉取 GHCR 镜像，不走本地构建：

```bash
cp .env.example .env
docker compose -f docker-compose.pull.yml up -d
```

查看日志：

```bash
docker compose -f docker-compose.pull.yml logs -f
```

停止服务：

```bash
docker compose -f docker-compose.pull.yml down
```

如果还要删除 MongoDB 数据卷：

```bash
docker compose -f docker-compose.pull.yml down -v
```

## 5. 运行已发布镜像

如果你已经有可用的 MongoDB，可以直接运行：

```powershell
docker run -d `
  --name "quant-trading" `
  -p "8000:8000" `
  --env-file ".env" `
  -e "MONGODB_URI=mongodb://host.docker.internal:27017" `
  -v "${PWD}/data:/app/data" `
  -v "${PWD}/logs:/app/logs" `
  "ghcr.io/<你的 GitHub 用户名>/quant-trading:latest"
```

如果希望继续用 Compose，也可以把 `docker-compose.yml` 中的 `app.build` 删除，改成仅保留 `image`。

## 6. 配置说明

容器内支持以下环境变量：

- `LLM_API_KEY`
- `LLM_API_BASE`
- `LLM_MODEL`
- `JWT_SECRET_KEY`
- `TUSHARE_TOKEN`
- `MONGODB_URI`
- `MONGODB_DB_NAME`
- `SQLITE_PATH`
- `LOG_LEVEL`
- `LOG_FILE`
- `INIT_ADMIN_USERNAME`
- `INIT_ADMIN_PASSWORD`

`config/config.yaml` 现在支持 `${VAR}` 和 `${VAR:-default}` 格式，占位符会在启动时自动展开。

## 7. 发布注意事项

- GHCR 默认镜像地址为 `ghcr.io/<owner>/<repo>`
- 当前工作流显式使用镜像名 `quant-trading`，避免仓库名不满足容器镜像命名规则时发布失败
- 如果希望任何人都能直接 `docker pull`，需要把 GitHub Packages 中对应镜像设为公开
- 当前工作流默认发布 `linux/amd64`，这是为了降低三方量化依赖的跨架构构建风险
