import discord
import wavelink
from discord import app_commands
from discord.ext import commands

from bot.services.music import MusicError


class Music(commands.Cog):
    """Lavalink-backed voice playback and per-guild queues."""

    def __init__(self, bot):
        self.bot = bot

    def _voice_channel(self, interaction: discord.Interaction) -> discord.VoiceChannel:
        member = interaction.user
        if not isinstance(member, discord.Member) or member.voice is None or member.voice.channel is None:
            raise MusicError("Join a voice channel before requesting music.")
        return member.voice.channel

    async def _play(self, interaction: discord.Interaction, query: str) -> None:
        try:
            channel = self._voice_channel(interaction)
            count, title = await self.bot.music.play(interaction.guild, channel, query)
        except MusicError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return

        if count == 1:
            await interaction.followup.send(f"Now playing **{title}**.")
        else:
            await interaction.followup.send(f"Added **{count} tracks** from **{title}** to the queue.")

    async def _action(self, interaction: discord.Interaction, action: str) -> None:
        operations = {
            "skip": (self.bot.music.skip, "Skipped the current track.", "Nothing is playing."),
            "stop": (self.bot.music.stop, "Stopped playback and cleared the queue.", "There is no active player."),
            "pause": (self.bot.music.pause, "Playback paused.", "Nothing is playing."),
            "resume": (self.bot.music.resume, "Playback resumed.", "Playback is not paused."),
        }
        operation, success, missing = operations[action]
        changed = await operation(interaction.guild)
        await interaction.followup.send(success if changed else missing, ephemeral=not changed)

    @app_commands.command(name="play", description="Play a track or playlist in your voice channel")
    @app_commands.guild_only()
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(thinking=True)
        await self._play(interaction, query)

    @app_commands.command(name="skip", description="Skip the current track")
    @app_commands.guild_only()
    async def skip(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._action(interaction, "skip")

    @app_commands.command(name="stop", description="Stop playback and clear the queue")
    @app_commands.guild_only()
    async def stop(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._action(interaction, "stop")

    @app_commands.command(name="pause", description="Pause music playback")
    @app_commands.guild_only()
    async def pause(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._action(interaction, "pause")

    @app_commands.command(name="resume", description="Resume music playback")
    @app_commands.guild_only()
    async def resume(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._action(interaction, "resume")

    @app_commands.command(name="queue", description="Show the current music queue")
    @app_commands.guild_only()
    async def queue(self, interaction: discord.Interaction):
        tracks = self.bot.music.queue(interaction.guild_id)
        if not tracks:
            return await interaction.response.send_message("The queue is empty.", ephemeral=True)
        lines = [f"{index}. [{track.title}]({track.uri})" for index, track in enumerate(tracks[:10], 1)]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="music-status", description="Show music node and player status")
    @app_commands.guild_only()
    async def status(self, interaction: discord.Interaction):
        node = self.bot.music.node
        if node is None:
            message = "Music is offline. Configure a reachable Lavalink v4 node."
        else:
            message = f"Music node **{node.identifier}** is connected."
        await interaction.response.send_message(message, ephemeral=True)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        if payload.player is not None and payload.reason in {"finished", "stopped"}:
            await self.bot.music.advance_finished_track(payload.player)


async def setup(bot):
    await bot.add_cog(Music(bot))
