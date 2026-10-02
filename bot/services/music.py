from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque

import discord
import wavelink

log = logging.getLogger(__name__)


class MusicError(Exception):
    """An expected error that can be shown to a music command user."""


class MusicService:
    def __init__(self, bot, url: str, password: str):
        self.bot = bot
        self.url = url.strip()
        self.password = password
        self.node: wavelink.Node | None = None
        self.queues: dict[int, deque[wavelink.Playable]] = defaultdict(deque)
        self._locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    @property
    def configured(self) -> bool:
        return bool(self.url and self.password)

    async def start(self) -> bool:
        if not self.configured:
            log.info("Music is disabled: LAVALINK_URL or LAVALINK_PASSWORD is missing")
            return False

        node = wavelink.Node(
            uri=self.url,
            password=self.password,
            inactive_player_timeout=None,
        )
        try:
            await wavelink.Pool.connect(client=self.bot, nodes=[node])
        except Exception:
            log.exception("Could not connect to the configured Lavalink node")
            return False

        self.node = node
        log.info("Connected music node %s", node.identifier)
        return True

    async def close(self) -> None:
        if self.node is not None:
            await wavelink.Pool.close()
            self.node = None

    async def play(self, guild: discord.Guild, voice_channel: discord.VoiceChannel, query: str) -> tuple[int, str]:
        if self.node is None:
            raise MusicError("Music is unavailable. Configure and start the Lavalink node first.")

        try:
            results = await wavelink.Playable.search(query, node=self.node)
        except (wavelink.LavalinkLoadException, wavelink.LavalinkException) as exc:
            raise MusicError("The music node could not load that request.") from exc
        if not results:
            raise MusicError("No playable tracks were found for that request.")

        tracks = results.tracks if isinstance(results, wavelink.Playlist) else results
        async with self._locks[guild.id]:
            player = guild.voice_client
            if player is not None and player.channel != voice_channel:
                raise MusicError(f"I am already playing in {player.channel.mention}.")
            if player is None:
                player = await voice_channel.connect(cls=wavelink.Player, self_deaf=True)

            queue = self.queues[guild.id]
            queue.extend(tracks)
            queued_count = len(tracks)
            first_title = tracks[0].title
            if not player.playing and player.current is None:
                await player.play(queue.popleft())
            return queued_count, first_title

    async def skip(self, guild: discord.Guild) -> bool:
        player = guild.voice_client
        if not isinstance(player, wavelink.Player) or player.current is None:
            return False
        await player.stop()
        return True

    async def stop(self, guild: discord.Guild) -> bool:
        player = guild.voice_client
        if not isinstance(player, wavelink.Player):
            return False
        async with self._locks[guild.id]:
            self.queues[guild.id].clear()
            if player.current is not None:
                await player.stop()
        return True

    async def pause(self, guild: discord.Guild) -> bool:
        player = guild.voice_client
        if not isinstance(player, wavelink.Player) or not player.playing:
            return False
        await player.pause(True)
        return True

    async def resume(self, guild: discord.Guild) -> bool:
        player = guild.voice_client
        if not isinstance(player, wavelink.Player) or not player.paused:
            return False
        await player.pause(False)
        return True

    def queue(self, guild_id: int) -> list[wavelink.Playable]:
        return list(self.queues[guild_id])

    async def advance_finished_track(self, player: wavelink.Player) -> None:
        if player.guild is None:
            return
        async with self._locks[player.guild.id]:
            await self._start_next(player.guild.id, player)

    async def _start_next(self, guild_id: int, player: wavelink.Player) -> None:
        queue = self.queues[guild_id]
        if queue and player.connected and not player.playing:
            await player.play(queue.popleft())