from types import SimpleNamespace

from bot.core import db as db_module


def _settings(*, pgbouncer):
    return SimpleNamespace(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/app",
        db_statement_timeout_ms=5000,
        db_use_pgbouncer=pgbouncer,
        db_pool_size=5,
        db_max_overflow=5,
        db_pool_timeout=10.0,
        db_pool_recycle=1800,
    )


def test_pgbouncer_disables_asyncpg_and_sqlalchemy_statement_caches(monkeypatch):
    captured = {}

    def fake_create_async_engine(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(db_module, "create_async_engine", fake_create_async_engine)
    monkeypatch.setattr(db_module, "async_sessionmaker", lambda *args, **kwargs: object())

    db_module.Database(_settings(pgbouncer=True))

    assert captured["kwargs"]["connect_args"]["statement_cache_size"] == 0
    assert "prepared_statement_cache_size" not in captured["kwargs"]["connect_args"]
    assert captured["url"].query["prepared_statement_cache_size"] == "0"


def test_regular_database_connection_does_not_force_pgbouncer_options(monkeypatch):
    captured = {}

    def fake_create_async_engine(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(db_module, "create_async_engine", fake_create_async_engine)
    monkeypatch.setattr(db_module, "async_sessionmaker", lambda *args, **kwargs: object())

    db_module.Database(_settings(pgbouncer=False))

    assert "statement_cache_size" not in captured["kwargs"]["connect_args"]
    assert "prepared_statement_cache_size" not in captured["url"].query
