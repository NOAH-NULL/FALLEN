from __future__ import annotations

from io import BytesIO
from pathlib import PurePath
from urllib.parse import urlparse

import discord
from discord import app_commands
from discord.ext import commands


DANGEROUS_ROLE_PERMISSIONS = (
    "administrator", "manage_guild", "manage_roles", "manage_channels",
    "manage_webhooks", "manage_messages", "kick_members", "ban_members",
    "moderate_members", "mention_everyone", "manage_nicknames",
    "manage_emojis_and_stickers", "manage_events", "manage_expressions",
    "manage_threads", "view_audit_log",
)


class RoleToggleButton(discord.ui.Button):
    def __init__(self, view, slot_number: int, *, label: str, custom_id: str, disabled: bool, row: int = 0):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, custom_id=custom_id, disabled=disabled, row=row)
        self.slot_number = slot_number

    async def callback(self, interaction: discord.Interaction):
        await self.view._toggle(interaction, self.slot_number)


class RulesPanelView(discord.ui.View):
    """Four persistent role-toggle buttons; state is always read from the DB."""

    def __init__(self, cog: "Rules", guild_id: int, panel: dict):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = int(guild_id)
        slots = panel.get("buttons") or []
        for index in range(4):
            slot = slots[index] if index < len(slots) else {}
            role_id = slot.get("role_id")
            label = (slot.get("label") or "").strip() or f"Button {index + 1}"
            self.add_item(RoleToggleButton(
                self, index + 1, label=label[:80],
                custom_id=f"fallen:rules:{self.guild_id}:{index + 1}",
                disabled=not role_id, row=0,
            ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None or interaction.guild.id != self.guild_id:
            await interaction.response.send_message(
                "This rules panel belongs to a different server.", ephemeral=True
            )
            return False
        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item):
        self.cog.bot.log.error("rules panel button failed: %r", error, exc_info=(type(error), error, error.__traceback__))
        if interaction.response.is_done():
            await interaction.followup.send(
                "The role toggle failed. Check the bot's role permissions.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "The role toggle failed. Check the bot's role permissions.", ephemeral=True
            )

    async def _toggle(self, interaction: discord.Interaction, slot_number: int):
        guild = interaction.guild
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "This button only works inside the server.", ephemeral=True
            )

        settings = await self.cog.bot.welcome_engine.get(guild.id)
        panel = settings.get("rules_panel") or {}
        slots = panel.get("buttons") or []
        if slot_number > len(slots):
            return await interaction.response.send_message(
                "This access button is not configured.", ephemeral=True
            )
        slot = slots[slot_number - 1]
        role_id = slot.get("role_id")
        role = guild.get_role(int(role_id)) if role_id else None
        if role is None:
            return await interaction.response.send_message(
                "This access button is not configured yet.", ephemeral=True
            )

        me = guild.me
        if me is None or not me.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                "FALLEN needs the Manage Roles permission to change access roles.", ephemeral=True
            )
        if role.is_default() or role.managed or role >= me.top_role:
            return await interaction.response.send_message(
                "That role can no longer be assigned. Ask an administrator to reconfigure this button.",
                ephemeral=True,
            )
        if any(getattr(role.permissions, name, False) for name in DANGEROUS_ROLE_PERMISSIONS):
            return await interaction.response.send_message(
                "This role has elevated permissions and cannot be self-assigned.", ephemeral=True
            )

        member = interaction.user
        try:
            if role in member.roles:
                await member.remove_roles(role, reason="FALLEN rules-panel access toggle")
                message = f"Removed {role.name}."
            else:
                await member.add_roles(role, reason="FALLEN rules-panel access toggle")
                message = f"Added {role.name}. Channels configured for this role should now be accessible."
        except discord.Forbidden:
            return await interaction.response.send_message(
                "Discord denied the role change. Check FALLEN's role hierarchy and Manage Roles permission.",
                ephemeral=True,
            )
        except discord.HTTPException:
            return await interaction.response.send_message(
                "Discord could not update your role. Please try again.", ephemeral=True
            )
        await interaction.response.send_message(message, ephemeral=True)


class Rules(commands.Cog):
    rules = app_commands.Group(name="rules", description="Create and manage a custom server rules panel")

    def __init__(self, bot):
        self.bot = bot
        self._registered_messages: set[int] = set()

    async def _reply(self, interaction: discord.Interaction, content, **kwargs):
        if interaction.response.is_done():
            return await interaction.followup.send(content, **kwargs)
        return await self._reply(interaction,content, **kwargs)

    async def _panel(self, guild_id: int) -> dict | None:
        settings = await self.bot.welcome_engine.get(guild_id)
        panel = settings.get("rules_panel")
        return dict(panel) if isinstance(panel, dict) else None

    async def _save_panel(self, guild_id: int, panel: dict) -> None:
        await self.bot.welcome_engine.save(guild_id, rules_panel=panel)

    @staticmethod
    def _embed(panel: dict) -> discord.Embed:
        title = str(panel.get("title") or "").strip()
        description = str(panel.get("description") or "").strip()
        parts = [description] if description else []
        for number, rule in enumerate(panel.get("rules") or [], 1):
            rule_title = str(rule.get("title") or "").strip()
            rule_text = str(rule.get("text") or "").strip()
            parts.append(f"**{number}. {rule_title}**\n{rule_text}")
        full_description = "\n\n".join(parts)
        if len(title) > 256:
            raise ValueError("The embed title cannot exceed 256 characters.")
        if len(full_description) > 4096:
            raise ValueError("The title, description, and rules exceed Discord's 4,096-character description limit.")
        if len(title) + len(full_description) > 5800:
            raise ValueError("The rules panel exceeds Discord's total embed character limit.")
        embed = discord.Embed(
            title=title or None,
            description=full_description or None,
            colour=discord.Colour.blurple(),
        )
        image_url = panel.get("image_url")
        image_filename = panel.get("image_filename")
        if image_url:
            embed.set_image(url=image_url)
        elif image_filename:
            embed.set_image(url=f"attachment://{image_filename}")
        return embed

    @staticmethod
    def _validate_panel(panel: dict) -> None:
        if not str(panel.get("title") or "").strip():
            raise ValueError("The rules panel title cannot be empty.")
        if not str(panel.get("description") or "").strip():
            raise ValueError("The rules panel description cannot be empty.")
        Rules._embed(panel)
        rules = panel.get("rules") or []
        if not isinstance(rules, list):
            raise ValueError("Stored rules data is invalid.")
        for rule in rules:
            if not isinstance(rule, dict) or not str(rule.get("title", "")).strip() or not str(rule.get("text", "")).strip():
                raise ValueError("Every rule needs both a title and description.")

    def _view(self, guild_id: int, panel: dict) -> RulesPanelView:
        return RulesPanelView(self, guild_id, panel)

    async def _sync_panel(self, guild: discord.Guild, panel: dict, *, upload: discord.File | None = None, clear_attachments: bool = False):
        channel_id = panel.get("channel_id")
        channel = guild.get_channel(int(channel_id)) if channel_id else None
        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            raise ValueError("Choose a valid text channel with a rules panel configured.")
        me = guild.me
        if me is None:
            raise ValueError("FALLEN cannot resolve its server member.")
        perms = channel.permissions_for(me)
        if not perms.view_channel or not perms.send_messages or not perms.embed_links:
            raise ValueError("FALLEN needs View Channel, Send Messages, and Embed Links in the rules channel.")
        self._validate_panel(panel)
        embed = self._embed(panel)
        view = self._view(guild.id, panel)
        message = None
        message_id = panel.get("message_id")
        if message_id:
            try:
                message = await channel.fetch_message(int(message_id))
            except (discord.NotFound, discord.Forbidden):
                message = None
        if message is None:
            # A deleted panel cannot retain its old uploaded attachment; do not
            # publish a broken attachment:// reference on a replacement message.
            if panel.get("image_filename") and upload is None:
                panel["image_filename"] = None
                embed = self._embed(panel)
            if upload is not None:
                sent = await channel.send(embed=embed, view=view, file=upload, allowed_mentions=discord.AllowedMentions.none())
            else:
                sent = await channel.send(embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none())
            panel["message_id"] = sent.id
            self._registered_messages.add(sent.id)
            return sent
        edit_kwargs = {"embed": embed, "view": view, "allowed_mentions": discord.AllowedMentions.none()}
        if upload is not None:
            edit_kwargs["attachments"] = [upload]
        elif clear_attachments:
            edit_kwargs["attachments"] = []
        await message.edit(**edit_kwargs)
        self._registered_messages.add(message.id)
        return message

    async def _require_panel(self, interaction: discord.Interaction) -> dict | None:
        panel = await self._panel(interaction.guild_id)
        if not panel:
            await interaction.response.send_message(
                "Set up the panel first with /rules setup.", ephemeral=True
            )
            return None
        return panel

    async def _report_error(self, interaction: discord.Interaction, error: Exception):
        if isinstance(error, ValueError):
            message = str(error)
        elif isinstance(error, discord.Forbidden):
            message = "Discord denied the action. Check FALLEN's channel permissions and role hierarchy."
        elif isinstance(error, discord.HTTPException):
            message = "Discord could not update the rules panel. Check channel permissions and try again."
        else:
            self.bot.log.exception("rules panel operation failed", exc_info=error)
            message = "The rules panel operation failed. Check FALLEN's logs."
        if interaction.response.is_done():
            await interaction.followup.send("❌ " + message, ephemeral=True)
        else:
            await interaction.response.send_message("❌ " + message, ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            try:
                panel = await self._panel(guild.id)
                if not panel or not panel.get("message_id"):
                    continue
                message_id = int(panel["message_id"])
                if message_id in self._registered_messages:
                    continue
                self.bot.add_view(self._view(guild.id, panel), message_id=message_id)
                self._registered_messages.add(message_id)
            except Exception:
                self.bot.log.exception("could not restore persistent rules view for guild=%s", guild.id)

    @rules.command(name="setup", description="Create or reset your custom rules panel")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_panel(self, interaction: discord.Interaction, title: app_commands.Range[str, 1, 256], description: app_commands.Range[str, 1, 3000], channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        previous = await self._panel(interaction.guild_id)
        reuse_message_id = (
            previous.get("message_id")
            if previous and int(previous.get("channel_id") or 0) == channel.id
            else None
        )
        panel = {
            "title": title.strip(),
            "description": description.strip(),
            "rules": [],
            "buttons": [
                {"label": "Button 1", "role_id": None},
                {"label": "Button 2", "role_id": None},
                {"label": "Button 3", "role_id": None},
                {"label": "Button 4", "role_id": None},
            ],
            "channel_id": channel.id,
            "message_id": reuse_message_id,
            "image_url": None,
            "image_filename": None,
        }
        try:
            self._validate_panel(panel)
            await self._save_panel(interaction.guild_id, panel)
            await self._sync_panel(interaction.guild, panel, clear_attachments=True)
            await self._save_panel(interaction.guild_id, panel)
            if previous and previous.get("message_id") and not reuse_message_id:
                old_channel = interaction.guild.get_channel(int(previous.get("channel_id") or 0))
                if old_channel is not None:
                    try:
                        old_message = await old_channel.fetch_message(int(previous["message_id"]))
                        await old_message.delete(reason="FALLEN rules panel replaced by an administrator")
                    except (discord.NotFound, discord.Forbidden):
                        pass
            await interaction.response.send_message(
                f"Rules panel created in {channel.mention}. Add rules with /rules add and configure all four buttons with /rules button.",
                ephemeral=True,
            )
        except Exception as exc:
            await self._report_error(interaction, exc)

    @rules.command(name="add", description="Add a rule written by your administrators")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add_rule(self, interaction: discord.Interaction, title: app_commands.Range[str, 1, 100], text: app_commands.Range[str, 1, 1000]):
        await interaction.response.defer(ephemeral=True)
        panel = await self._require_panel(interaction)
        if panel is None:
            return
        panel.setdefault("rules", []).append({"title": title.strip(), "text": text.strip()})
        try:
            self._validate_panel(panel)
            await self._save_panel(interaction.guild_id, panel)
            await self._sync_panel(interaction.guild, panel)
            await self._save_panel(interaction.guild_id, panel)
            await interaction.response.send_message(f"Rule {len(panel['rules'])} added and the panel updated.", ephemeral=True)
        except Exception as exc:
            await self._report_error(interaction, exc)

    @rules.command(name="edit", description="Edit an existing rule by its number")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def edit_rule(self, interaction: discord.Interaction, number: app_commands.Range[int, 1, 1000], title: app_commands.Range[str, 1, 100] | None = None, text: app_commands.Range[str, 1, 1000] | None = None):
        await interaction.response.defer(ephemeral=True)
        panel = await self._require_panel(interaction)
        if panel is None:
            return
        rules = panel.get("rules") or []
        if number > len(rules):
            return await interaction.response.send_message("That rule number does not exist.", ephemeral=True)
        if title is None and text is None:
            return await interaction.response.send_message("Provide a new title, new text, or both.", ephemeral=True)
        if title is not None:
            rules[number - 1]["title"] = title.strip()
        if text is not None:
            rules[number - 1]["text"] = text.strip()
        try:
            self._validate_panel(panel)
            await self._save_panel(interaction.guild_id, panel)
            await self._sync_panel(interaction.guild, panel)
            await self._save_panel(interaction.guild_id, panel)
            await interaction.response.send_message(f"Rule {number} edited and the panel updated.", ephemeral=True)
        except Exception as exc:
            await self._report_error(interaction, exc)

    @rules.command(name="remove", description="Remove a rule by its number")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove_rule(self, interaction: discord.Interaction, number: app_commands.Range[int, 1, 1000]):
        await interaction.response.defer(ephemeral=True)
        panel = await self._require_panel(interaction)
        if panel is None:
            return
        rules = panel.get("rules") or []
        if number > len(rules):
            return await interaction.response.send_message("That rule number does not exist.", ephemeral=True)
        removed = rules.pop(number - 1)
        try:
            self._validate_panel(panel)
            await self._save_panel(interaction.guild_id, panel)
            await self._sync_panel(interaction.guild, panel)
            await self._save_panel(interaction.guild_id, panel)
            await interaction.response.send_message(f"Removed rule: {removed['title']}.", ephemeral=True)
        except Exception as exc:
            await self._report_error(interaction, exc)

    @rules.command(name="button", description="Configure one of the four role-access toggle buttons")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def configure_button(self, interaction: discord.Interaction, slot: app_commands.Range[int, 1, 4], label: app_commands.Range[str, 1, 80], role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        panel = await self._require_panel(interaction)
        if panel is None:
            return
        guild = interaction.guild
        me = guild.me
        actor = interaction.user
        if not label.strip():
            return await self._reply(interaction, "Button label cannot be blank.", ephemeral=True)
        if role.is_default() or role.managed:
            return await interaction.response.send_message("Choose a normal, assignable server role.", ephemeral=True)
        if any(getattr(role.permissions, name, False) for name in DANGEROUS_ROLE_PERMISSIONS):
            return await interaction.response.send_message("That role has elevated permissions and cannot be self-assigned.", ephemeral=True)
        if me is None or not me.guild_permissions.manage_roles or role >= me.top_role:
            return await interaction.response.send_message("FALLEN needs Manage Roles and a top role above the selected role.", ephemeral=True)
        if not isinstance(actor, discord.Member) or (guild.owner_id != actor.id and role >= actor.top_role):
            return await interaction.response.send_message("You can only configure roles below your own highest role.", ephemeral=True)
        buttons = panel.setdefault("buttons", [])
        while len(buttons) < 4:
            buttons.append({"label": f"Button {len(buttons) + 1}", "role_id": None})
        if any(index != slot - 1 and item.get("role_id") == role.id for index, item in enumerate(buttons)):
            return await interaction.response.send_message("Each access button must use a different role.", ephemeral=True)
        buttons[slot - 1] = {"label": label.strip(), "role_id": role.id}
        try:
            await self._save_panel(interaction.guild_id, panel)
            await self._sync_panel(guild, panel)
            await self._save_panel(interaction.guild_id, panel)
            await interaction.response.send_message(f"Button {slot} is now **{label.strip()}** for {role.mention}. Make sure the role has access only to the intended channels.", ephemeral=True)
        except Exception as exc:
            await self._report_error(interaction, exc)

    @rules.command(name="publish", description="Publish or refresh the rules panel")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def publish_panel(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None):
        await interaction.response.defer(ephemeral=True)
        panel = await self._require_panel(interaction)
        if panel is None:
            return
        if channel is not None:
            panel["channel_id"] = channel.id
        try:
            await self._sync_panel(interaction.guild, panel)
            await self._save_panel(interaction.guild_id, panel)
            target = interaction.guild.get_channel(int(panel["channel_id"]))
            await interaction.response.send_message(f"Rules panel published or refreshed in {target.mention}.", ephemeral=True)
        except Exception as exc:
            await self._report_error(interaction, exc)

    @rules.command(name="edit-panel", description="Change the rules panel title or description")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def edit_panel(self, interaction: discord.Interaction, title: app_commands.Range[str, 1, 256] | None = None, description: app_commands.Range[str, 1, 3000] | None = None):
        await interaction.response.defer(ephemeral=True)
        panel = await self._require_panel(interaction)
        if panel is None:
            return
        if title is None and description is None:
            return await interaction.response.send_message("Provide a new title, a new description, or both.", ephemeral=True)
        if title is not None:
            panel["title"] = title.strip()
        if description is not None:
            panel["description"] = description.strip()
        try:
            self._validate_panel(panel)
            await self._save_panel(interaction.guild_id, panel)
            await self._sync_panel(interaction.guild, panel)
            await self._save_panel(interaction.guild_id, panel)
            await interaction.response.send_message("Rules panel title/description updated.", ephemeral=True)
        except Exception as exc:
            await self._report_error(interaction, exc)

    @rules.command(name="image", description="Attach an image or GIF to the rules embed")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_image(self, interaction: discord.Interaction, attachment: discord.Attachment):
        await interaction.response.defer(ephemeral=True)
        panel = await self._require_panel(interaction)
        if panel is None:
            return
        content_type = (attachment.content_type or "").lower()
        suffix = PurePath(attachment.filename).suffix.lower()
        allowed = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
        if not (content_type.startswith("image/") or suffix in allowed) or suffix not in allowed:
            return await interaction.response.send_message("Upload a PNG, JPG, WEBP, or GIF image.", ephemeral=True)
        if attachment.size > int(interaction.guild.filesize_limit):
            return await interaction.response.send_message(f"This server's upload limit is {interaction.guild.filesize_limit // (1024 * 1024)} MB.", ephemeral=True)
        try:
            data = await attachment.read()
            filename = "rules-image" + suffix
            panel["image_url"] = None
            panel["image_filename"] = filename
            await self._save_panel(interaction.guild_id, panel)
            await self._sync_panel(interaction.guild, panel, upload=discord.File(BytesIO(data), filename=filename))
            await self._save_panel(interaction.guild_id, panel)
            await interaction.response.send_message("Image/GIF attached and the panel updated.", ephemeral=True)
        except Exception as exc:
            await self._report_error(interaction, exc)

    @rules.command(name="image-url", description="Set the rules embed image using an HTTPS URL")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_image_url(self, interaction: discord.Interaction, url: app_commands.Range[str, 1, 1024]):
        await interaction.response.defer(ephemeral=True)
        panel = await self._require_panel(interaction)
        if panel is None:
            return
        parsed = urlparse(url.strip())
        if parsed.scheme != "https" or not parsed.netloc:
            return await interaction.response.send_message("Use a valid HTTPS image/GIF URL.", ephemeral=True)
        panel["image_url"] = url.strip()
        panel["image_filename"] = None
        try:
            await self._save_panel(interaction.guild_id, panel)
            await self._sync_panel(interaction.guild, panel, clear_attachments=True)
            await self._save_panel(interaction.guild_id, panel)
            await interaction.response.send_message("Rules image URL saved and the panel updated.", ephemeral=True)
        except Exception as exc:
            await self._report_error(interaction, exc)

    @rules.command(name="remove-image", description="Remove the rules embed image")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove_image(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        panel = await self._require_panel(interaction)
        if panel is None:
            return
        panel["image_url"] = None
        panel["image_filename"] = None
        try:
            await self._save_panel(interaction.guild_id, panel)
            await self._sync_panel(interaction.guild, panel, clear_attachments=True)
            await self._save_panel(interaction.guild_id, panel)
            await interaction.response.send_message("Rules image removed.", ephemeral=True)
        except Exception as exc:
            await self._report_error(interaction, exc)

    @rules.command(name="status", description="Show the current rules panel configuration")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def panel_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        panel = await self._panel(interaction.guild_id)
        if not panel:
            return await interaction.response.send_message("No rules panel is configured. Use /rules setup.", ephemeral=True)
        rules = panel.get("rules") or []
        buttons = panel.get("buttons") or []
        lines = [
            f"Title: {panel.get('title') or '(empty)'}",
            f"Channel: <#{panel.get('channel_id')}>" if panel.get("channel_id") else "Channel: not set",
            f"Rules: {len(rules)}",
            f"Image: {'configured' if panel.get('image_url') or panel.get('image_filename') else 'none'}",
        ]
        for index in range(4):
            item = buttons[index] if index < len(buttons) else {}
            role_id = item.get("role_id")
            lines.append(f"Button {index + 1}: {item.get('label') or 'unlabelled'} → <@&{role_id}>" if role_id else f"Button {index + 1}: not configured")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Rules(bot))
