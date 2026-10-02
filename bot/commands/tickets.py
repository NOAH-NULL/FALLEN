from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
from bot.ui import success_embed, error_embed

class Tickets(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @app_commands.command(name='ticket',description='Create a private support ticket')
    async def ticket(self,i):
        await i.response.defer(ephemeral=True)
        ch=await self.bot.tickets.create(i.guild,None,i.user)
        await self.bot.extreme.ticket_create(i.guild_id,ch.id,i.user.id)
        await ch.send(f'🎫 Welcome {i.user.mention}. Staff can help you here.')
        await i.followup.send(embed=success_embed('Ticket created', f'Your private support channel is {ch.mention}.'),ephemeral=True)
    @app_commands.command(name='close',description='Close the current ticket')
    async def close(self,i):
        row=await self.bot.extreme.ticket_get(i.channel.id)
        owner_id = None
        if getattr(i.channel, 'topic', None) and 'fallen-ticket-owner:' in i.channel.topic:
            try: owner_id = int(i.channel.topic.split('fallen-ticket-owner:', 1)[1].split()[0])
            except ValueError: owner_id = None
        allowed = i.user.guild_permissions.manage_channels or owner_id == i.user.id
        if not allowed:
            return await i.response.send_message(embed=error_embed('Close denied', 'Only the ticket creator or a channel manager can close this ticket.'),ephemeral=True)
        if not row and not i.channel.name.startswith('ticket-'):
            return await i.response.send_message(embed=error_embed('Not a ticket', 'This command can only close a ticket channel.'),ephemeral=True)
        await self.bot.extreme.ticket_update(i.channel.id,status='closed')
        await i.response.send_message('Closing ticket…')
        await i.channel.delete(reason='Ticket closed')
async def setup(bot): await bot.add_cog(Tickets(bot))
