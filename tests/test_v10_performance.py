from pathlib import Path


def test_prefix_commands_have_fast_lane_before_heavy_message_work():
    src = Path('bot/core/bot.py').read_text()
    fast = src.index('if message.content.startswith(self.command_prefix):')
    cfg = src.index('cfg=await self.guild_config.get(message.guild.id)', fast)
    invoke = src.index('await self.invoke(ctx)', fast)
    assert invoke < cfg


def test_release_name_is_v10():
    src = Path('scripts/build_release.py').read_text()
    assert 'Fallen-v1.0-performance-first.zip' in src
