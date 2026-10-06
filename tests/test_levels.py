from bot.services.levels import LevelService


def test_reference_xp_thresholds():
    assert LevelService.xp_needed(0) == 0
    assert LevelService.xp_needed(1) == 100
    assert LevelService.xp_needed(2) == 255
    assert LevelService.xp_needed(3) == 475
    assert LevelService.xp_needed(10) == 4675
    assert LevelService.xp_needed(100) == 1899250


def test_level_from_total_xp_edges():
    assert LevelService.level_from_total_xp(0) == 0
    assert LevelService.level_from_total_xp(99) == 0
    assert LevelService.level_from_total_xp(100) == 1
    assert LevelService.level_from_total_xp(254) == 1
    assert LevelService.level_from_total_xp(255) == 2
    assert LevelService.level_from_total_xp(474) == 2
    assert LevelService.level_from_total_xp(475) == 3
    assert LevelService.level_from_total_xp(1899250) == 100
    assert LevelService.level_from_total_xp(999999999) == 100


def test_thresholds_are_strictly_increasing():
    thresholds = LevelService.XP_THRESHOLDS
    assert len(thresholds) == 101
    assert all(a < b for a, b in zip(thresholds, thresholds[1:]))


def test_message_xp_ceiling_matches_reference_limit():
    assert LevelService.MAX_MESSAGE_XP == 75


def test_character_count_ignores_spaces_and_punctuation():
    assert LevelService.character_count("Hello, world! 123") == 10
    assert LevelService.character_count("!!!") == 0


def test_character_xp_respects_letter_count():
    assert min(75, LevelService.character_count("hello") * 2) == 10
