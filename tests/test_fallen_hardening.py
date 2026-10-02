from pathlib import Path
from bot.services.extreme import FEATURES, DEFAULTS, ExtremeService


def test_every_catalog_feature_has_runtime_default():
    names = {n for values in FEATURES.values() for n in values}
    assert names == ExtremeService.all_names()
    assert names == set(DEFAULTS)
    assert len(names) == 100


def test_v16_prefix_surface_is_not_duplicated_in_legacy_text_cog():
    text = Path('bot/commands/text.py').read_text()
    assert "commands.group(name='v16'" not in text
    extreme = Path('bot/commands/extreme.py').read_text()
    assert "hybrid_group(name='v16'" in extreme


def test_secret_material_is_not_checked_in():
    assert not Path('pgbouncer-userlist.txt').exists()
    assert 'password=discordbot' not in Path('pgbouncer.ini').read_text()
    assert 'POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in .env' in Path('docker-compose.yml').read_text()


def test_alembic_chain_ends_at_capability_migration():
    migration = Path('alembic/versions/0010_warning_expiration.py').read_text()
    assert "down_revision='0009_v16_capabilities'" in migration
    assert Path('alembic/versions/0009_v16_capabilities.py').exists()
