from pathlib import Path


def test_prefix_command_errors_are_centralized():
    source = Path("bot/core/bot.py").read_text()
    handler = Path("bot/core/prefix_errors.py").read_text()
    assert "handle_prefix_command_error" in source
    assert "MissingRequiredArgument" in handler
    assert "BadArgument" in handler


def test_community_embed_supports_thumbnail_keyword():
    source = Path("bot/ui/embeds.py").read_text()
    assert "thumbnail: str | None = None" in source
    assert "embed.set_thumbnail" in source


def test_prefix_daily_is_rate_limited():
    source = Path("bot/commands/text.py").read_text()
    assert "daily:{ctx.guild.id}:{ctx.author.id}" in source
    assert "self.bot.limiter.allow" in source


def test_tickets_grant_staff_access_and_record_owner():
    source = Path("bot/services/tickets.py").read_text()
    assert "manage_channels" in source
    assert "fallen-ticket-owner:" in source


def test_custom_command_output_blocks_mentions():
    source = Path("bot/commands/custom.py").read_text()
    assert "AllowedMentions.none()" in source


def test_lockdown_uses_persistent_state_snapshot():
    source = Path("bot/core/bot.py").read_text()
    assert 'snapshot_save' in source
    assert '__lockdown__' in source
    assert 'snapshot_delete' in source


def test_economy_updates_are_row_locked():
    source = Path("bot/services/platform.py").read_text()
    assert "on_conflict_do_nothing" in source
    assert "with_for_update" in source


def test_xp_updates_are_row_locked():
    source = Path("bot/services/levels.py").read_text()
    assert "on_conflict_do_nothing" in source
    assert "with_for_update" in source
