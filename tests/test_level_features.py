from pathlib import Path
from bot.services.levels import LevelService

def test_xp_threshold_scales():
    assert LevelService.xp_needed(0) == 100
    assert LevelService.xp_needed(4) == 500

def test_community_source_has_level_uwu_and_level_roles():
    source = Path('bot/commands/community.py').read_text()
    assert "name='level'" in source
    assert "name='uwuify'" in source
    assert "name='levelrole'" in source
    assert "name='levelrole-remove'" in source
    assert "name='levelroles'" in source

def test_text_source_has_uwu_and_levelrole():
    source = Path('bot/commands/text.py').read_text()
    assert "name='uwuify'" in source
    assert "name='levelrole'" in source
