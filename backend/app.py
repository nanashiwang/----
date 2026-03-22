import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.auth.jwt_handler import validate_jwt_config
from backend.routers import (
    agents,
    admin_logs,
    auth,
    backtest,
    knowledge,
    market_data,
    ml,
    news,
    recommend,
    review,
    settings,
    sources,
    trades,
    users,
    workflow,
)
from src.data.db.mongo_client import MongoDBClient
from src.data.db.sqlite_client import SQLiteClient
from src.utils.config import get_config

_sqlite_client = None
_mongo_client = None
_news_scheduler = None
_market_data_scheduler = None


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


app = FastAPI(title="多 Agent 量化交易系统", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin_logs.router)
app.include_router(settings.router)
app.include_router(agents.router)
app.include_router(sources.router)
app.include_router(news.router)
app.include_router(market_data.router)
app.include_router(recommend.router)
app.include_router(review.router)
app.include_router(knowledge.router)
app.include_router(backtest.router)
app.include_router(trades.router)
app.include_router(workflow.router)
app.include_router(ml.router)


@app.on_event("startup")
async def startup():
    global _news_scheduler
    global _market_data_scheduler

    validate_jwt_config()
    db = get_sqlite_client()

    from backend.services.news_scheduler import NewsScheduler, should_disable_scheduler
    from backend.services.market_data_scheduler import (
        MarketDataScheduler,
        should_disable_market_data_scheduler,
    )
    from backend.services.settings_service import AgentConfigService, SettingsService
    from backend.services.source_service import SourceService
    from backend.services.user_service import UserService

    UserService(db).ensure_admin_exists()
    SettingsService(db).seed_defaults()
    AgentConfigService(db).seed_defaults()
    SourceService(db).seed_defaults()

    if not should_disable_scheduler():
        _news_scheduler = NewsScheduler(db)
        _news_scheduler.start()
    if not should_disable_market_data_scheduler():
        _market_data_scheduler = MarketDataScheduler(db)
        _market_data_scheduler.start()


@app.on_event("shutdown")
async def shutdown():
    global _news_scheduler
    global _market_data_scheduler
    if _news_scheduler is not None:
        _news_scheduler.shutdown()
        _news_scheduler = None
    if _market_data_scheduler is not None:
        _market_data_scheduler.shutdown()
        _market_data_scheduler = None


@app.get("/api/health")
async def health():
    return {"status": "ok"}


_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file = _frontend_dist / full_path
        if file.exists() and file.is_file():
            return FileResponse(str(file))
        return FileResponse(str(_frontend_dist / "index.html"))
