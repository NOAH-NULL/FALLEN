"""Dynamic, searchable help for the commands that are actually registered.

Both prefix and application-command help use the same command inventory. This
module deliberately never advertises roadmap-only or unregistered commands.
"""
from __future__ import annotations

from typing import Iterable
import discord
from discord import app_commands
from discord.ext import commands

PAGE_SIZE = 10


def _clean(value: str, limit: int = 90) -> str:
    value = " ".join((value or "").split())
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _category(command: commands.Command) -> str:
    cog = getattr(command, "cog", None)
    name = getattr(cog, "qualified_name", None) or getattr(cog, "__cog_name__", None)
    if name:
        return name
    root = command.qualified_name.split(" ", 1)[0]
    return root.title()


def _prefix_inventory(bot: commands.Bot) -> list[tuple[str, str, str]]:
    """Return registered prefix commands only, excluding hidden commands."""
    items: list[tuple[str, str, str]] = []
    for command in bot.walk_commands():
        if command.hidden:
            continue
        # Groups are useful help entries too; subcommands appear independently.
        usage = command.signature.strip()
        syntax = f"{bot.command_prefix}{command.qualified_name}"
        if usage:
            syntax += f" {usage}"
        items.append((_category(command), syntax, command.short_doc or command.help or "No description provided."))
    return items


def _slash_inventory(bot: commands.Bot) -> list[tuple[str, str, str]]:
    """Walk registered application commands, including nested command groups."""
    items: list[tuple[str, str, str]] = []

    def visit(command, prefix: str = "") -> None:
        qualified = f"{prefix} {command.name}".strip()
        children = getattr(command, "commands", None)
        if children:
            for child in children:
                visit(child, qualified)
        else:
            description = getattr(command, "description", "") or "No description provided."
            items.append(("Slash Commands", f"/{qualified}", description))

    for command in bot.tree.get_commands():
        visit(command)
    return items


def _inventory(bot: commands.Bot) -> list[tuple[str, str, str]]:
    # Prefix and slash interfaces are shown separately so users can discover
    # the interface they can invoke. Deduplicate only exact interface entries.
    seen: set[tuple[str, str]] = set()
    result = []
    for category, syntax, description in _prefix_inventory(bot) + _slash_inventory(bot):
        key = (category, syntax)
        if key not in seen:
            seen.add(key)
            result.append((category, syntax, description))
    return sorted(result, key=lambda item: (item[0].casefold(), item[1].casefold()))


class HelpPager(discord.ui.View):
    def __init__(self, entries: list[tuple[str, str, str]], title: str, *, page: int = 0):
        super().__init__(timeout=120)
        self.entries = entries
        self.title_text = title
        self.page = page
        self.message: discord.Message | None = None
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        pages = max(1, (len(self.entries) + PAGE_SIZE - 1) // PAGE_SIZE)
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == "help:prev":
                child.disabled = self.page <= 0
            elif isinstance(child, discord.ui.Button) and child.custom_id == "help:next":
                child.disabled = self.page >= pages - 1

    def make_embed(self) -> discord.Embed:
        pages = max(1, (len(self.entries) + PAGE_SIZE - 1) // PAGE_SIZE)
        start = self.page * PAGE_SIZE
        chunk = self.entries[start:start + PAGE_SIZE]
        embed = discord.Embed(
            title=self.title_text,
            description=(f"**{len(self.entries)} registered entries** · Page {self.page + 1}/{pages}\n"
                         "Use `,help command-name` or `/help` with a search term for details."),
            colour=discord.Colour.blurple(),
        )
        if not chunk:
            empty_text = "No commands are currently registered." if not self.entries else "No matching commands. Try a shorter search term."
            embed.add_field(name="No matching commands", value=empty_text, inline=False)
        else:
            for category, syntax, description in chunk:
                embed.add_field(name=_clean(syntax, 240), value=f"{_clean(description, 180)}\n*{category}*", inline=False)
        embed.set_footer(text="Only registered commands are listed. Some actions require server permissions.")
        return embed

    async def _refresh(self, interaction: discord.Interaction) -> None:
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, custom_id="help:prev")
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.page = max(0, self.page - 1)
        await self._refresh(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, custom_id="help:next")
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        pages = max(1, (len(self.entries) + PAGE_SIZE - 1) // PAGE_SIZE)
        self.page = min(pages - 1, self.page + 1)
        await self._refresh(interaction)

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass


# Backwards-compatible descriptive alias used by older internal tests.
HelpPages = HelpPager


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _registered_entries(self) -> list[tuple[str, str, str]]:
        seen: set[tuple[str, str]] = set()
        result = []
        for category, syntax, description in _prefix_inventory(self.bot) + _slash_inventory(self.bot):
            key = (category, syntax)
            if key not in seen:
                seen.add(key)
                result.append((category, syntax, description))
        return sorted(result, key=lambda item: (item[0].casefold(), item[1].casefold()))

    async def _send_prefix(self, ctx: commands.Context, query: str = "") -> None:
        entries = self._registered_entries()
        if query:
            needle = query.casefold().strip()
            entries = [entry for entry in entries if needle in entry[1].casefold() or needle in entry[2].casefold() or needle in entry[0].casefold()]
            title = f"Help search: {query[:80]}"
        else:
            title = "TITAN · Command Help"
        view = HelpPages(entries, title)
        message = await ctx.send(embed=view.make_embed(), view=view)
        view.message = message

    @commands.command(name="help", aliases=["commands", "cmds"], help="Browse registered prefix and slash commands. Optional search term.")
    async def prefix_help(self, ctx: commands.Context, *, query: str = "") -> None:
        await self._send_prefix(ctx, query)

    @app_commands.command(name="help", description="Browse and search registered bot commands")
    @app_commands.describe(query="Optional command/category search")
    async def slash_help(self, interaction: discord.Interaction, query: str = "") -> None:
        entries = self._registered_entries()
        if query.strip():
            needle = query.casefold().strip()
            entries = [entry for entry in entries if needle in entry[1].casefold() or needle in entry[2].casefold() or needle in entry[0].casefold()]
            title = f"Help search: {query[:80]}"
        else:
            title = "TITAN · Command Help"
        view = HelpPages(entries, title)
        await interaction.response.send_message(embed=view.make_embed(), view=view, ephemeral=True)
        try:
            view.message = await interaction.original_response()
        except discord.HTTPException:
            pass

    @commands.command(name="help-category", aliases=["helpcat"] , help="List registered commands in one category.")
    async def prefix_category(self, ctx: commands.Context, *, category: str) -> None:
        needle = category.casefold().strip()
        entries = [entry for entry in _inventory(self.bot) if needle in entry[0].casefold()]
        view = HelpPages(entries, f"Help category: {category[:80]}")
        message = await ctx.send(embed=view.make_embed(), view=view)
        view.message = message


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Help(bot))
