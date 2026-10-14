import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlsplit, unquote

from app.infrastructure.config.settings import DBSettings
from app.infrastructure.database import postgres


class SettingsTests(unittest.TestCase):
    def test_credentials_round_trip_reserved_characters(self):
        config = DBSettings(_env_file=None, user="user space", password="p a+ss/@:#")
        uri = urlsplit(config.db_dsn)
        self.assertEqual(unquote(uri.username), "user space")
        self.assertEqual(unquote(uri.password), "p a+ss/@:#")


class PoolStartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_start_closes_partial_pool(self):
        candidate = MagicMock()
        candidate.open = AsyncMock(side_effect=RuntimeError("database unavailable"))
        candidate.close = AsyncMock()
        config = SimpleNamespace(db_dsn="postgresql://localhost/test", min_size=1,
                                 max_size=2, timeout_conn=1, appname="c01_test")
        with patch.object(postgres, "settings", SimpleNamespace(db=config)), \
             patch.object(postgres.psycopg_pool, "AsyncConnectionPool", return_value=candidate):
            with self.assertRaisesRegex(RuntimeError, "database unavailable"):
                await postgres.init_pool.__wrapped__()
        candidate.close.assert_awaited_once()
        self.assertIsNone(postgres.pool)
