import pytest

from bot.core.shard_lease import resolve_shard_ids


def test_explicit_shard_ids_are_preserved():
    assert resolve_shard_ids([2, 0], configured_count=4) == [2, 0]


def test_configured_shard_count_leases_every_shard():
    assert resolve_shard_ids(None, configured_count=3) == [0, 1, 2]


def test_auto_sharding_uses_discord_recommended_count():
    assert resolve_shard_ids(None, recommended_count=5) == [0, 1, 2, 3, 4]


def test_single_shard_fallback_is_explicit():
    assert resolve_shard_ids(None) == [0]


@pytest.mark.parametrize("ids", [[], [-1], [0, 0]])
def test_invalid_explicit_shard_ids_are_rejected(ids):
    with pytest.raises(ValueError):
        resolve_shard_ids(ids)


@pytest.mark.parametrize("count", [0, -1])
def test_invalid_shard_counts_are_rejected(count):
    with pytest.raises(ValueError):
        resolve_shard_ids(None, configured_count=count)


def test_explicit_shard_ids_must_fit_configured_count():
    with pytest.raises(ValueError, match="smaller than SHARD_COUNT"):
        resolve_shard_ids([4], configured_count=4)
