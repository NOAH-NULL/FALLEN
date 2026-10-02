from bot.services.extreme import FEATURES

def test_v16_has_exactly_100_feature_switches():
    names=[n for group in FEATURES.values() for n in group]
    assert len(names)==100
    assert len(set(names))==100

def test_v16_has_nine_feature_domains():
    assert list(FEATURES)==[
        'security','moderation','automod','leveling','community',
        'engagement','music','tickets','administration'
    ]
