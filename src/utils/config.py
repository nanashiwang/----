from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
import yaml


class LLMConfig(BaseSettings):
    provider: str = "openai"
    api_base: str = "https://api.openai.com/v1"
    api_key: str
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2000


class TushareConfig(BaseSettings):
    token: str


class MongoDBConfig(BaseSettings):
    uri: str = "mongodb://localhost:27017"
    db_name: str = "quant_trading"


class SQLiteConfig(BaseSettings):
    path: str = "data/sqlite/trading.db"


class DatabaseConfig(BaseSettings):
    mongodb: MongoDBConfig
    sqlite: SQLiteConfig


class LoggingConfig(BaseSettings):
    level: str = "INFO"
    file: str = "logs/app.log"


class Config(BaseSettings):
    llm: LLMConfig
    tushare: TushareConfig
    database: DatabaseConfig
    logging: LoggingConfig

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return cls(**data)


_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.load()
    return _config
