from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware

from apps.api.deps import get_app_settings, get_session_manager
from apps.api.responses import ApiResponse
from apps.api.routes import api_router
from core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title='Quant Research Platform', version='3.0.0')
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    @app.on_event('startup')
    def startup() -> None:
        settings = get_app_settings()
        if settings.auto_init_schema:
            get_session_manager().init_schema()

    @app.get('/api/health')
    def health() -> dict[str, str]:
        return {'status': 'ok'}

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ApiResponse(success=False, error=str(exc.detail)).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_exception(_, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=ApiResponse(success=False, error='request validation failed', meta={'details': exc.errors()}).model_dump(),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(_, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=ApiResponse(success=False, error=exc.__class__.__name__, meta={'message': str(exc)}).model_dump(),
        )

    app.include_router(api_router)
    return app


app = create_app()
