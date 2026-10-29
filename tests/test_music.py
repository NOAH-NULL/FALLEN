import asyncio

from bot.services.music import MusicService


def test_music_is_disabled_without_lavalink_configuration():
    service = MusicService(object(), '', '')

    assert service.configured is False
    assert asyncio.run(service.start()) is False


def test_music_registers_lavalink_node_without_idle_player_timeout(monkeypatch):
    service = MusicService(object(), 'http://localhost:2333', 'secret')
    connected = {}

    async def fake_connect(*, client, nodes):
        connected['client'] = client
        connected['node'] = nodes[0]
        return {'default': nodes[0]}

    monkeypatch.setattr('bot.services.music.wavelink.Pool.connect', fake_connect)
    # The mock registers a node but does not simulate the websocket handshake.
    assert asyncio.run(service.start()) is False

    assert connected['node']._inactive_player_timeout is None
    assert service.node is connected['node']
    asyncio.run(connected['node']._session.close())