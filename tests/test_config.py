import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import Config


class TestConfig(unittest.TestCase):
    """测试配置加载"""

    def test_load_supports_env_placeholders_and_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_dir = temp_path / "config"
            config_dir.mkdir()

            config_file = config_dir / "config.yaml"
            config_file.write_text(
                textwrap.dedent(
                    """
                    llm:
                      provider: "openai"
                      api_base: "https://api.openai.com/v1"
                      api_key: "${TEST_LLM_API_KEY}"
                      model: "gpt-4"
                      temperature: 0.7
                      max_tokens: 2000

                    tushare:
                      token: "${TEST_TUSHARE_TOKEN}"
                      api_url: "${TEST_TUSHARE_API_URL:-}"

                    market_data:
                      symbols: "${TEST_MARKET_DATA_SYMBOLS:-000001.SZ,600519.SH}"
                      data_types: "${TEST_MARKET_DATA_TYPES:-daily,daily_basic,moneyflow,index_daily}"
                      benchmark_index_codes: "${TEST_MARKET_DATA_BENCHMARK_INDEX_CODES:-000300.SH,000905.SH}"
                      primary_benchmark: "${TEST_MARKET_DATA_PRIMARY_BENCHMARK:-000300.SH}"
                      fetch_interval: "${TEST_MARKET_DATA_FETCH_INTERVAL:-3600}"
                      history_days: "${TEST_MARKET_DATA_HISTORY_DAYS:-30}"
                      start_date: "${TEST_MARKET_DATA_START_DATE:-}"
                      end_date: "${TEST_MARKET_DATA_END_DATE:-}"
                      auto_sync: "${TEST_MARKET_DATA_AUTO_SYNC:-false}"

                    database:
                      mongodb:
                        uri: "${TEST_MONGODB_URI:-mongodb://mongo:27017}"
                        db_name: "${TEST_MONGODB_DB_NAME:-quant_trading}"
                      sqlite:
                        path: "${TEST_SQLITE_PATH:-data/sqlite/trading.db}"

                    logging:
                      level: "${TEST_LOG_LEVEL:-INFO}"
                      file: "${TEST_LOG_FILE:-logs/app.log}"
                    """
                ).strip(),
                encoding="utf-8",
            )

            os.environ["TEST_LLM_API_KEY"] = "llm-key"
            os.environ["TEST_TUSHARE_TOKEN"] = "ts-token"
            try:
                config = Config.load(str(config_file))
            finally:
                os.environ.pop("TEST_LLM_API_KEY", None)
                os.environ.pop("TEST_TUSHARE_TOKEN", None)

            self.assertEqual(config.llm.api_key, "llm-key")
            self.assertEqual(config.tushare.token, "ts-token")
            self.assertEqual(config.tushare.api_url, "")
            self.assertEqual(config.market_data.symbols, "000001.SZ,600519.SH")
            self.assertEqual(config.market_data.data_types, "daily,daily_basic,moneyflow,index_daily")
            self.assertEqual(config.market_data.benchmark_index_codes, "000300.SH,000905.SH")
            self.assertEqual(config.market_data.primary_benchmark, "000300.SH")
            self.assertEqual(config.market_data.fetch_interval, 3600)
            self.assertEqual(config.market_data.history_days, 30)
            self.assertEqual(config.market_data.start_date, "")
            self.assertEqual(config.market_data.end_date, "")
            self.assertFalse(config.market_data.auto_sync)
            self.assertEqual(config.database.mongodb.uri, "mongodb://mongo:27017")
            self.assertEqual(config.database.sqlite.path, "data/sqlite/trading.db")
            self.assertEqual(config.logging.file, "logs/app.log")

    def test_load_raises_for_missing_required_env(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_dir = temp_path / "config"
            config_dir.mkdir()

            config_file = config_dir / "config.yaml"
            config_file.write_text(
                textwrap.dedent(
                    """
                    llm:
                      provider: "openai"
                      api_base: "https://api.openai.com/v1"
                      api_key: "${MISSING_LLM_API_KEY}"
                      model: "gpt-4"
                      temperature: 0.7
                      max_tokens: 2000

                    tushare:
                      token: "token"
                      api_url: ""

                    market_data:
                      symbols: "000001.SZ"
                      data_types: "daily"
                      benchmark_index_codes: "000300.SH"
                      primary_benchmark: "000300.SH"
                      fetch_interval: 3600
                      history_days: 10
                      start_date: ""
                      end_date: ""
                      auto_sync: false

                    database:
                      mongodb:
                        uri: "mongodb://localhost:27017"
                        db_name: "quant_trading"
                      sqlite:
                        path: "data/sqlite/trading.db"

                    logging:
                      level: "INFO"
                      file: "logs/app.log"
                    """
                ).strip(),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "缺少必需的环境变量"):
                Config.load(str(config_file))
