from __future__ import annotations
import discord

class TicketService:
    async def create(self,guild,category,member):
        overwrites={
            guild.default_role:discord.PermissionOverwrite(view_channel=False),
            member:discord.PermissionOverwrite(view_channel=True,send_messages=True,read_message_history=True),
        }
        staff_roles = [role for role in guild.roles if not role.is_default() and role.permissions.manage_channels]
        for role in staff_roles:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        me = guild.me
        if me:
            overwrites[me] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True)
        return await guild.create_text_channel(
            f'ticket-{member.name}'.lower()[:90], category=category, overwrites=overwrites,
            topic=f'fallen-ticket-owner:{member.id}', reason='Ticket created')
