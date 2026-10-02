import logging
import discord
from discord import app_commands

log = logging.getLogger("bot.commands")


def _message(error: app_commands.AppCommandError) -> str:
    if isinstance(error, app_commands.errors.MissingPermissions):
        return "You don't have permission to use this command."
    if isinstance(error, app_commands.errors.BotMissingPermissions):
        return "I don't have the Discord permissions required for that action."
    if isinstance(error, app_commands.errors.CommandOnCooldown):
        return f"Please wait **{error.retry_after:.1f}s** before trying again."
    if isinstance(error, app_commands.errors.TransformerError):
        return "One of the supplied values is invalid. Please check the command options."
    if isinstance(error, app_commands.errors.CheckFailure):
        return "This command cannot be used here or with your current permissions."
    return "Something went wrong while running that command. The error has been logged."


async def handle_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    original = getattr(error, "original", error)
    if not isinstance(error, (app_commands.errors.MissingPermissions,
                              app_commands.errors.BotMissingPermissions,
                              app_commands.errors.CommandOnCooldown,
                              app_commands.errors.TransformerError,
                              app_commands.errors.CheckFailure)):
        log.exception("application command failed", exc_info=original)
    embed = discord.Embed(title="✕ Command failed", description=_message(error), colour=discord.Colour.red())
    embed.set_footer(text="Fallen • Try /help for command usage")
    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.HTTPException:
        log.debug("could not send application command error response", exc_info=True)
