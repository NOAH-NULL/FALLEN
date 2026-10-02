import logging
import discord
from discord.ext import commands

log = logging.getLogger('bot.commands')


def _message(error: commands.CommandError) -> str:
    if isinstance(error, commands.MissingPermissions):
        return 'You do not have permission to use that command.'
    if isinstance(error, commands.BotMissingPermissions):
        return 'I am missing a Discord permission required for that action.'
    if isinstance(error, commands.MissingRequiredArgument):
        return f'Missing **{error.param.name}**. Use `{getattr(error.command, "name", "help")}` help for the correct format.'
    if isinstance(error, commands.BadArgument):
        return 'One of the supplied values could not be understood. Mention a member/channel/role or use a valid number.'
    if isinstance(error, commands.CommandNotFound):
        return 'That command does not exist. Try `,help`.'
    if isinstance(error, commands.NoPrivateMessage):
        return 'This command can only be used inside a server.'
    if isinstance(error, commands.CommandOnCooldown):
        return f'Please wait **{error.retry_after:.1f}s** before trying again.'
    return 'Something went wrong while running that command. The error has been logged.'


async def handle_prefix_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    original = getattr(error, 'original', error)
    if not isinstance(error, (commands.MissingPermissions, commands.BotMissingPermissions,
                              commands.MissingRequiredArgument, commands.BadArgument,
                              commands.CommandNotFound, commands.NoPrivateMessage,
                              commands.CommandOnCooldown)):
        log.exception('prefix command failed', exc_info=original)
    embed = discord.Embed(title='✕ Command failed', description=_message(error), colour=discord.Colour.red())
    embed.set_footer(text='Fallen • Try help for command usage')
    try:
        await ctx.send(embed=embed, delete_after=12)
    except discord.HTTPException:
        log.debug('could not send prefix command error response', exc_info=True)
