from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
        protected_namespaces=('settings_',),
    )

    app_name: str = 'Quant Research Platform'
    api_prefix: str = '/api'

    postgres_dsn: str = Field(
        default='sqlite+pysqlite:///./data/sqlite/run_centric.db',
        validation_alias=AliasChoices('DATABASE_URL', 'POSTGRES_DSN'),
        alias='POSTGRES_DSN',
    )
    mongo_uri: str = Field(default='mongodb://localhost:27017', alias='MONGODB_URI')
    mongo_db: str = Field(default='quant_trading', alias='MONGODB_DB_NAME')
    auto_init_schema: bool = Field(default=False, alias='AUTO_INIT_SCHEMA')

    celery_broker_url: str = Field(default='redis://localhost:6379/0', alias='CELERY_BROKER_URL')
    celery_result_backend: str = Field(default='redis://localhost:6379/1', alias='CELERY_RESULT_BACKEND')

    tushare_token: str = Field(default='', alias='TUSHARE_TOKEN')
    tushare_api_url: str = Field(default='', alias='TUSHARE_API_URL')
    default_watchlist: str = Field(default='000001.SZ,600519.SH,300750.SZ', alias='DEFAULT_WATCHLIST')

    llm_provider: str = Field(default='stub', alias='LLM_PROVIDER')
    llm_api_key: str = Field(default='', alias='LLM_API_KEY')
    llm_api_base: str = Field(default='', alias='LLM_API_BASE')

    prompt_version: str = Field(default='prompt-v1', alias='PROMPT_VERSION')
    agent_version: str = Field(default='agent-v1', alias='AGENT_VERSION')
    feature_set_version: str = Field(default='feature-set-v1', alias='FEATURE_SET_VERSION')
    model_version: str = Field(default='model-v1', alias='MODEL_VERSION')

    hot_knowledge_tests_threshold: int = Field(default=5, alias='HOT_KNOWLEDGE_TESTS_THRESHOLD')
    hot_knowledge_pass_rate_threshold: float = Field(default=0.65, alias='HOT_KNOWLEDGE_PASS_RATE_THRESHOLD')

    mlflow_tracking_uri: str = Field(default='file:./mlruns', alias='MLFLOW_TRACKING_URI')
    vectorstore_uri: str = Field(default='memory://vectorstore', alias='VECTORSTORE_URI')


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
