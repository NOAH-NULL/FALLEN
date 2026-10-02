from bot.services.uwuify import UwuifyService

def test_uwuify_is_strong_and_preserves_links():
    out = UwuifyService.transform("I don't want to go to school today https://example.com", seed=7)
    assert 'https://example.com' in out
    assert out != "I don't want to go to school today https://example.com"
    assert any(x in out.lower() for x in ('w', 'uwu', '>w<', ';w;'))

def test_uwuify_does_not_change_code_or_mentions():
    text='hello <@123> `really`'
    out=UwuifyService.transform(text, seed=2)
    assert '<@123>' in out
    assert '`really`' in out
