import discord
from discord import app_commands
from discord.ext import commands


class Prefix(commands.Cog):
    """Per-server prefix configuration."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="prefix", invoke_without_command=True)
    @commands.guild_only()
    async def prefix(self, ctx):
        """Show this server's command prefix."""
        config = await self.bot.guild_config.get(ctx.guild.id)
        current = (config or {}).get("command_prefix") or ","
        await ctx.send(f"Current prefix: `{discord.utils.escape_markdown(current)}`")

    @prefix.command(name="set", description="Set this server's command prefix")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_prefix(self, ctx, prefix: str):
        prefix = prefix.strip()
        if not prefix or len(prefix) > 5 or any(char.isspace() for char in prefix):
            await ctx.send("Choose a prefix between 1 and 5 characters with no spaces.")
            return
        if prefix.startswith("<@") or prefix.startswith("<#"):
            await ctx.send("Mentions cannot be used as a command prefix.")
            return
        await self.bot.guild_config.update(ctx.guild.id, command_prefix=prefix)
        await ctx.send(
            f"Prefix updated to `{discord.utils.escape_markdown(prefix)}`. "
            "Commands will now use the new prefix."
        )

    @prefix.command(name="reset", description="Reset this server's prefix to the default")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def reset_prefix(self, ctx):
        await self.bot.guild_config.update(ctx.guild.id, command_prefix=",")
        await ctx.send("Prefix reset to `,`.")

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need **Manage Server** permission to change the prefix.")
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Usage: `prefix set <new-prefix>`")
            return
        raise error


async def setup(bot):
    await bot.add_cog(Prefix(bot))
