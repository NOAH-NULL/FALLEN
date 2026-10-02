from bot.core.config import Settings
def test_settings(monkeypatch):
    monkeypatch.setenv('DISCORD_TOKEN','abcdefghij123456'); monkeypatch.setenv('DATABASE_URL','postgresql+asyncpg://x:y@localhost/x'); s=Settings(); assert s.db_pool_size==5 and s.db_max_overflow==5
