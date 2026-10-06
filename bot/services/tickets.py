from __future__ import annotations
import discord
from discord.ext import commands

class TicketService:
    async def create(self, guild, category, member):
        if guild is None or member is None:
            raise ValueError("ticket creation requires a guild and member")
        overwrites={
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        staff_roles = [
            role for role in guild.roles
            if not role.is_default() and role.permissions.manage_channels
        ]
        for role in staff_roles:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            )
        me = guild.me
        if me:
            overwrites[me] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True, manage_channels=True
            )

        base = f"ticket-{member.id}"
        existing = discord.utils.find(
            lambda ch: getattr(ch, "topic", "") == f"fallen-ticket-owner:{member.id}",
            guild.text_channels,
        )
        if existing:
            return existing

        return await guild.create_text_channel(
            base[:90],
            category=category,
            overwrites=overwrites,
            topic=f"fallen-ticket-owner:{member.id}",
            reason="Ticket created",
        )
