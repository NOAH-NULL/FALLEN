from pathlib import Path


def test_v15_invite_tracker_uses_redis_buffer_and_singleflight():
    src=Path('bot/services/invites.py').read_text()
    assert 'invite-buffer:' in src
    assert 'acquire_lock' in src
    assert 'hincrby' in src
    assert 'rename_if_exists' in src
    assert 'ON CONFLICT (guild_id,user_id)' in src


def test_v15_join_path_is_not_blocked_by_invite_http_lookup():
    src=Path('bot/core/bot.py').read_text()
    join=src.split('    async def process_member_join',1)[1].split('    async def process_member_remove',1)[0]
    assert 'antiraid.observe' in join
    assert 'invites.submit_join' in join
    assert 'identify_join' not in join


def test_v15_raid_sheds_welcome_work():
    src=Path('bot/core/bot.py').read_text()
    assert 'suppress_greeting=raid' in src
    assert 'shedding welcome work' in src


def test_v15_persists_member_invite_attribution():
    model=Path('bot/models/extended.py').read_text()
    migration=Path('alembic/versions/0006_member_invite_attribution.py').read_text()
    assert 'member_invite_attribution' in model
    assert 'UniqueConstraint(\'guild_id\',\'member_id\')' in model
    assert 'member_invite_attribution' in migration


def test_v15_greeting_queue_sheds_stale_jobs():
    src=Path('bot/workers/greetings.py').read_text()
    assert 'max_event_age' in src
    assert 'dropping stale greeting' in src


def test_v15_alembic_chain_is_linear():
    files = {
        '0001': Path('alembic/versions/0001_initial.py').read_text(),
        '0002': Path('alembic/versions/0002_platform.py').read_text(),
        '0003': Path('alembic/versions/0003_levels_roles.py').read_text(),
        '0004': Path('alembic/versions/0004_greeting_embeds.py').read_text(),
        '0005': Path('alembic/versions/0005_invite_stats.py').read_text(),
        '0006': Path('alembic/versions/0006_member_invite_attribution.py').read_text(),
        '0007': Path('alembic/versions/0007_runtime_schema.py').read_text(),
    }
    assert "revision='0001'; down_revision=None" in files['0001']
    assert "revision='0002';down_revision='0001'" in files['0002']
    assert "revision='0003'; down_revision='0002'" in files['0003']
    assert 'revision="0004"' in files['0004'] and 'down_revision="0003"' in files['0004']
    assert "revision = '0005_invite_stats'" in files['0005'] and "down_revision = '0004'" in files['0005']
    assert "revision='0006_member_invite_attribution'" in files['0006'] and "down_revision='0005_invite_stats'" in files['0006']
    assert 'revision = "0007_runtime_schema"' in files['0007'] and 'down_revision = "0006_member_invite_attribution"' in files['0007']


def test_v15_guild_config_model_contains_persisted_embed_and_timestamp_fields():
    src = Path('bot/models/schema.py').read_text()
    for field in ('welcome_embed_enabled', 'goodbye_embed_enabled', 'welcome_embed_title',
                  'goodbye_embed_title', 'welcome_embed_description', 'goodbye_embed_description',
                  'welcome_embed_color', 'goodbye_embed_color', 'created_at', 'updated_at'):
        assert field in src


def test_v15_prefix_root_has_no_levelrole_collision():
    src = Path('bot/commands/text.py').read_text()
    assert "@commands.group(name='levelrole'" in src
    assert "@commands.command(name='levelrole')" not in src


def test_v15_security_raid_status_uses_service_api():
    src = Path('bot/commands/security.py').read_text()
    assert 'self.bot.antiraid.count' in src
    assert 'self.bot.antiraid.joins' not in src
