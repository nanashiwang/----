import sys
from pathlib import Path

# 确保项目根目录在路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.auth.jwt_handler import validate_jwt_config
from src.utils.config import get_config
from src.data.db.sqlite_client import SQLiteClient
from src.data.db.mongo_client import MongoDBClient
from src.data.sources.tushare_api import TushareAPI
from src.llm.factory import LLMFactory

from backend.routers import auth, users, settings, agents, sources, recommend, review, knowledge, backtest, trades, workflow

# 全局实例
_sqlite_client = None
_mongo_client = None


def get_sqlite_client() -> SQLiteClient:
    global _sqlite_client
    if _sqlite_client is None:
        config = get_config()
        _sqlite_client = SQLiteClient(config.database.sqlite.path)
    return _sqlite_client


def get_mongo_client() -> MongoDBClient:
    global _mongo_client
    if _mongo_client is None:
        config = get_config()
        _mongo_client = MongoDBClient(config.database.mongodb.uri, config.database.mongodb.db_name)
    return _mongo_client


app = FastAPI(title="多Agent量化交易系统", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(settings.router)
app.include_router(agents.router)
app.include_router(sources.router)
app.include_router(recommend.router)
app.include_router(review.router)
app.include_router(knowledge.router)
app.include_router(backtest.router)
app.include_router(trades.router)
app.include_router(workflow.router)


@app.on_event("startup")
async def startup():
    validate_jwt_config()
    db = get_sqlite_client()
    from backend.services.user_service import UserService
    from backend.services.settings_service import SettingsService, AgentConfigService
    UserService(db).ensure_admin_exists()
    SettingsService(db).seed_defaults()
    AgentConfigService(db).seed_defaults()


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# 生产环境提供Vue前端静态文件
_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file = _frontend_dist / full_path
        if file.exists() and file.is_file():
            return FileResponse(str(file))
        return FileResponse(str(_frontend_dist / "index.html"))
