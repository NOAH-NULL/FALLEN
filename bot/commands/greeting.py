import string
import logging
import re
import discord
from discord import app_commands, ui
from discord.ext import commands

log = logging.getLogger(__name__)

KIND_CHOICES = [
    app_commands.Choice(name='Welcome', value='welcome'),
    app_commands.Choice(name='Goodbye', value='goodbye'),
]

ALLOWED_PLACEHOLDERS = {
    'mention', 'name', 'username', 'server', 'count',
    'membercount', 'inviter', 'inviter_name', 'invites',
    'account_age', 'account_created', 'joined_at',
    'boosts', 'server_id', 'user_id', 'avatar', 'server_icon',
}

URL_REGEX = re.compile(
    r'^(?:http|ftp)s?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)


def parse_color(val, default: int = 0x5865F2) -> int:
    """Safely parse hex/int color inputs with 24-bit color bounds safety."""
    if val is None:
        return default
    if isinstance(val, int):
        return val if 0 <= val <= 0xFFFFFF else default
    if isinstance(val, str):
        val = val.lstrip('#').replace('0x', '')
        try:
            res = int(val, 16)
            return res if 0 <= res <= 0xFFFFFF else default
        except ValueError:
            pass
    return default


def validate_template(value: str) -> str | None:
    if not value or not value.strip():
        return 'Message cannot be empty.'
    
    try:
        for _, field_name, _, _ in string.Formatter().parse(value):
            if field_name is None:
                continue
            if field_name == '' or field_name.isdigit():
                return 'Positional placeholders like `{}` or `{0}` are not supported.'
            
            base_field = field_name.split('.')[0].split('[')[0].split(':')[0].split('!')[0]
            if base_field not in ALLOWED_PLACEHOLDERS:
                return f'Unknown template variable: {{{field_name}}}.'
    except ValueError:
        return 'Invalid braces or format string in the message template.'

    # Test format execution against mock data
    try:
        value.format(
            mention='@user', name='Member', username='member', server='Server',
            count=100, membercount=100, inviter='Inviter', inviter_name='InviterName',
            invites=5, account_age='10 days', account_created='2024-01-01',
            joined_at='2026-01-01', boosts=0, server_id=123456789, user_id=987654321,
            avatar='https://cdn.discordapp.com/embed/avatars/0.png',
            server_icon='https://cdn.discordapp.com/embed/avatars/0.png'
        )
    except (KeyError, ValueError, IndexError, AttributeError) as err:
        return f'Invalid formatting syntax: {err}'
    return None


class TemplateEditModal(ui.Modal):
    def __init__(self, cog: "Greeting", kind: str, current_msg: str, current_title: str, current_image: str, current_footer: str):
        super().__init__(title=f'Edit {kind.title()} Template')
        self.cog = cog
        self.kind = kind

        default_title = (current_title or f"Welcome to {kind.title()}!")[:256]
        default_msg = (current_msg or "Welcome {mention} to {server}!")[:2048]
        default_image = (current_image or "")[:1024]
        default_footer = (current_footer or "User ID: {user_id}")[:2048]

        self.embed_title = ui.TextInput(
            label="Embed Title",
            style=discord.TextStyle.short,
            default=default_title,
            required=False,
            max_length=256
        )
        self.message = ui.TextInput(
            label="Greeting Message / Description",
            style=discord.TextStyle.paragraph,
            default=default_msg,
            required=True,
            max_length=2048
        )
        self.image_url = ui.TextInput(
            label="Banner Image/GIF URL (Optional)",
            placeholder="https://i.imgur.com/example.gif or {avatar}",
            style=discord.TextStyle.short,
            default=default_image,
            required=False,
            max_length=1024
        )
        self.footer_text = ui.TextInput(
            label="Embed Footer Text (Optional)",
            placeholder="User ID: {user_id} | Members: {count}",
            style=discord.TextStyle.short,
            default=default_footer,
            required=False,
            max_length=2048
        )

        self.add_item(self.embed_title)
        self.add_item(self.message)
        self.add_item(self.image_url)
        self.add_item(self.footer_text)

    async def on_submit(self, interaction: discord.Interaction):
        error = validate_template(self.message.value)
        if error:
            return await interaction.response.send_message(f'❌ {error}', ephemeral=True)

        if self.embed_title.value and self.embed_title.value.strip():
            title_error = validate_template(self.embed_title.value)
            if title_error:
                return await interaction.response.send_message(f'❌ Title Error: {title_error}', ephemeral=True)

        img_val = self.image_url.value.strip() if self.image_url.value else ""
        if img_val:
            img_error = validate_template(img_val)
            if img_error:
                return await interaction.response.send_message(f'❌ Image URL Error: {img_error}', ephemeral=True)

        footer_val = self.footer_text.value.strip() if self.footer_text.value else ""
        if footer_val:
            footer_error = validate_template(footer_val)
            if footer_error:
                return await interaction.response.send_message(f'❌ Footer Error: {footer_error}', ephemeral=True)

        await self.cog._save(
            interaction.guild_id,
            **{
                f'{self.kind}_message': self.message.value,
                f'{self.kind}_embed_title': self.embed_title.value.strip(),
                f'{self.kind}_image_url': img_val,
                f'{self.kind}_footer_text': footer_val
            }
        )
        await interaction.response.send_message(
            f'✅ Successfully updated **{self.kind.title()}** template!',
            ephemeral=True
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        log.error("Failed to save template via modal for guild %s", interaction.guild_id, exc_info=error)
        msg = "❌ An error occurred while saving your configuration. Please try again."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


class Greeting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    group = app_commands.Group(name='greeting', description='Advanced welcome and goodbye configuration')

    async def _save(self, guild_id: int, **values):
        await self.bot.guild_config.update(guild_id, **values)

    @staticmethod
    def _can_send(channel: discord.abc.GuildChannel, me: discord.Member, require_embed: bool = True) -> tuple[bool, str]:
        if me is None:
            return False, 'Bot Member instance unavailable'
        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            return False, 'Valid Text Channel or Thread'

        permissions = channel.permissions_for(me)
        missing = []
        if not permissions.view_channel:
            missing.append('View Channel')
        
        if isinstance(channel, discord.Thread):
            if not permissions.send_messages_in_threads:
                missing.append('Send Messages in Threads')
        elif not permissions.send_messages:
            missing.append('Send Messages')

        if not permissions.attach_files:
            missing.append('Attach Files')
        if require_embed and not permissions.embed_links:
            missing.append('Embed Links')
            
        return (len(missing) == 0, ', '.join(missing))

    def _format_placeholders(self, template: str, member: discord.Member, extra: dict = None) -> str:
        if not template:
            return ""

        guild = member.guild
        now = discord.utils.utcnow()
        created_days = max(0, (now - member.created_at).days)
        joined_str = member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "Unknown"
        member_count = guild.member_count or 0

        avatar_url = member.display_avatar.url
        server_icon_url = guild.icon.url if guild.icon else ""

        replacements = {
            'mention': member.mention,
            'name': member.display_name,
            'username': str(member),
            'server': guild.name,
            'count': member_count,
            'membercount': member_count,
            'inviter': extra.get('inviter', 'Unknown') if extra else 'Unknown',
            'inviter_name': extra.get('inviter_name', 'Unknown') if extra else 'Unknown',
            'invites': extra.get('invites', 0) if extra else 0,
            'account_age': f"{created_days} days",
            'account_created': member.created_at.strftime("%Y-%m-%d"),
            'joined_at': joined_str,
            'boosts': guild.premium_subscription_count or 0,
            'server_id': guild.id,
            'user_id': member.id,
            'avatar': avatar_url,
            'server_icon': server_icon_url,
        }
        try:
            return template.format(**replacements)
        except Exception as e:
            log.warning("Failed formatting template string '%s': %s", template, e)
            return template

    def build_embed(self, kind: str, member: discord.Member, cfg: dict, extra: dict = None) -> discord.Embed:
        guild_name = member.guild.name
        
        msg_template = cfg.get(f'{kind}_message', f'Welcome {{mention}} to {{server}}!')
        embed_title = cfg.get(f'{kind}_embed_title', f'Welcome to {guild_name}')
        embed_color = parse_color(cfg.get(f'{kind}_embed_color'))
        image_template = cfg.get(f'{kind}_image_url', '')

        formatted_msg = self._format_placeholders(msg_template, member, extra)
        formatted_title = self._format_placeholders(embed_title, member, extra)
        formatted_image = self._format_placeholders(image_template, member, extra).strip()

        embed = discord.Embed(
            title=formatted_title if formatted_title else None,
            description=formatted_msg,
            color=embed_color,
            timestamp=discord.utils.utcnow()
        )

        if cfg.get(f'{kind}_show_thumbnail', True):
            embed.set_thumbnail(url=member.display_avatar.url)

        if formatted_image:
            if URL_REGEX.match(formatted_image):
                embed.set_image(url=formatted_image)
            else:
                log.warning("Invalid image/GIF URL omitted from embed: %s", formatted_image)

        footer_text = cfg.get(f'{kind}_footer_text', f"User ID: {member.id}")
        formatted_footer = self._format_placeholders(footer_text, member, extra)
        if formatted_footer and cfg.get(f'{kind}_show_footer', True):
            embed.set_footer(
                text=formatted_footer,
                icon_url=member.guild.icon.url if member.guild.icon else None
            )

        return embed

    async def _send_greeting(self, kind: str, member: discord.Member):
        cfg = await self.bot.guild_config.get(member.guild.id)
        if not cfg.get(f'{kind}_enabled', True):
            return

        channel_id = cfg.get(f'{kind}_channel_id')
        if not channel_id:
            return

        channel = member.guild.get_channel(channel_id)
        if not channel:
            return

        use_embed = cfg.get(f'{kind}_embed_enabled', True)
        ok, missing = self._can_send(channel, member.guild.me, require_embed=use_embed)
        if not ok:
            log.warning("Cannot send %s in guild %s channel %s: Missing %s", kind, member.guild.id, channel_id, missing)
            return

        try:
            if use_embed:
                embed = self.build_embed(kind, member, cfg)
                await channel.send(embed=embed)
            else:
                msg_template = cfg.get(f'{kind}_message', f'Welcome {{mention}} to {{server}}!')
                formatted_msg = self._format_placeholders(msg_template, member)
                await channel.send(content=formatted_msg)
        except discord.HTTPException as e:
            log.error("Failed to send %s message in guild %s: %s", kind, member.guild.id, e)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        # 1. Assign Auto Roles
        cfg = await self.bot.guild_config.get(member.guild.id)
        settings = await self.bot.welcome_engine.get(member.guild.id, cfg)
        role_ids = settings.get('auto_role_ids', [])
        
        if role_ids:
            roles_to_add = [member.guild.get_role(rid) for rid in role_ids if member.guild.get_role(rid)]
            if roles_to_add:
                try:
                    await member.add_roles(*roles_to_add, reason="Greeting Cog Auto-Role Assignment")
                except discord.HTTPException as e:
                    log.error("Failed to assign auto roles to %s in guild %s: %s", member.id, member.guild.id, e)

        # 2. Dispatch Welcome Message
        await self._send_greeting('welcome', member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return
        await self._send_greeting('goodbye', member)

    @group.command(name='edit', description='Interactively edit templates using a popup modal')
    @app_commands.guild_only()
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def edit(self, interaction: discord.Interaction, kind: str):
        cfg = await self.bot.guild_config.get(interaction.guild_id)
        current_msg = cfg.get(f'{kind}_message', '')
        current_title = cfg.get(f'{kind}_embed_title', '')
        current_image = cfg.get(f'{kind}_image_url', '')
        current_footer = cfg.get(f'{kind}_footer_text', '')
        modal = TemplateEditModal(self, kind, current_msg, current_title, current_image, current_footer)
        await interaction.response.send_modal(modal)

    @group.command(name='toggle', description='Enable or disable welcome or goodbye features')
    @app_commands.guild_only()
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def toggle(self, interaction: discord.Interaction, kind: str, state: bool):
        await self._save(interaction.guild_id, **{f'{kind}_enabled': state})
        status_str = "enabled" if state else "disabled"
        await interaction.response.send_message(f'✅ **{kind.title()}** notifications are now **{status_str}**.', ephemeral=True)

    @group.command(name='embed', description='Toggle embed mode vs plain text message mode')
    @app_commands.guild_only()
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def toggle_embed(self, interaction: discord.Interaction, kind: str, enable_embed: bool):
        await self._save(interaction.guild_id, **{f'{kind}_embed_enabled': enable_embed})
        mode = "Embeds" if enable_embed else "Plain Text Messages"
        await interaction.response.send_message(f'✅ **{kind.title()}** output mode set to **{mode}**.', ephemeral=True)

    @group.command(name='color', description='Set custom hex color for embed border')
    @app_commands.guild_only()
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_color(self, interaction: discord.Interaction, kind: str, hex_code: str):
        parsed = parse_color(hex_code, None)
        if parsed is None:
            return await interaction.response.send_message('❌ Invalid Hex color code. Example: `#5865F2` or `0xFF0000`.', ephemeral=True)

        await self._save(interaction.guild_id, **{f'{kind}_embed_color': parsed})
        await interaction.response.send_message(f'✅ Updated **{kind.title()}** embed color to `{hex_code}`.', ephemeral=True)

    @group.command(name='image', description='Set or remove an animated GIF or static image banner')
    @app_commands.guild_only()
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_image(self, interaction: discord.Interaction, kind: str, url: str | None = None):
        if url:
            url = url.strip()
            err = validate_template(url)
            if err:
                return await interaction.response.send_message(f'❌ {err}', ephemeral=True)

        await self._save(interaction.guild_id, **{f'{kind}_image_url': url or ''})
        if url:
            await interaction.response.send_message(f'✅ Updated **{kind.title()}** banner image/GIF URL.', ephemeral=True)
        else:
            await interaction.response.send_message(f'🗑️ Removed **{kind.title()}** banner image/GIF.', ephemeral=True)

    @group.command(name='preview', description='Preview how your configured greeting message will look')
    @app_commands.guild_only()
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def preview(self, interaction: discord.Interaction, kind: str):
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("❌ This command must be run inside a guild.", ephemeral=True)

        cfg = await self.bot.guild_config.get(interaction.guild_id)
        
        if cfg.get(f'{kind}_embed_enabled', True):
            embed = self.build_embed(kind, interaction.user, cfg)
            await interaction.response.send_message(
                content=f"👀 **[Preview] {kind.title()} Message:**",
                embed=embed,
                ephemeral=True
            )
        else:
            msg_template = cfg.get(f'{kind}_message', f'Welcome {{mention}} to {{server}}!')
            formatted_msg = self._format_placeholders(msg_template, interaction.user)
            await interaction.response.send_message(
                content=f"👀 **[Preview] {kind.title()} Message:**\n{formatted_msg}",
                ephemeral=True
            )

    @group.command(name='test', description='Send a live test message directly to the configured channel')
    @app_commands.guild_only()
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def test(self, interaction: discord.Interaction, kind: str):
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("❌ Commands must be run inside a guild.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        await self._send_greeting(kind, interaction.user)
        await interaction.followup.send(f"✅ Executed live test dispatch for **{kind.title()}**.", ephemeral=True)

    @group.command(name='channel', description='Set the target channel for welcome/goodbye messages')
    @app_commands.guild_only()
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def channel(
        self, 
        interaction: discord.Interaction, 
        kind: str, 
        channel: discord.TextChannel | discord.Thread
    ):
        me = interaction.guild.me if interaction.guild else None
        if me is None:
            return await interaction.response.send_message('❌ Cannot resolve bot permissions.', ephemeral=True)

        cfg = await self.bot.guild_config.get(interaction.guild_id)
        ok, missing = self._can_send(channel, me, require_embed=bool(cfg.get(f'{kind}_embed_enabled', True)))
        if not ok:
            return await interaction.response.send_message(
                f'❌ Permission check failed for {channel.mention}. Missing: **{missing}**.',
                ephemeral=True
            )

        await self._save(interaction.guild_id, **{f'{kind}_channel_id': channel.id})
        await interaction.response.send_message(f'✅ {kind.title()} channel updated to {channel.mention}.')

    @group.command(name='roles', description='Configure roles automatically assigned when a member joins')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def roles(
        self,
        interaction: discord.Interaction,
        role1: discord.Role = None,
        role2: discord.Role = None,
        role3: discord.Role = None,
        role4: discord.Role = None,
        role5: discord.Role = None,
    ):
        selected_roles = list({r for r in (role1, role2, role3, role4, role5) if r})
        me = interaction.guild.me if interaction.guild else None
        invoker = interaction.user

        if me and isinstance(invoker, discord.Member):
            bot_invalid = [r for r in selected_roles if r >= me.top_role]
            user_invalid = [
                r for r in selected_roles
                if r >= invoker.top_role and interaction.guild.owner_id != invoker.id
            ]
            managed_roles = [r for r in selected_roles if r.managed or r.is_default()]

            if bot_invalid:
                return await interaction.response.send_message(
                    '❌ Cannot assign roles higher than or equal to my highest role: ' +
                    ', '.join(r.mention for r in bot_invalid),
                    ephemeral=True
                )
            if user_invalid:
                return await interaction.response.send_message(
                    '❌ You cannot configure roles higher than or equal to your own top role: ' +
                    ', '.join(r.mention for r in user_invalid),
                    ephemeral=True
                )
            if managed_roles:
                return await interaction.response.send_message(
                    '❌ Integration, managed, or @everyone roles cannot be auto-assigned: ' +
                    ', '.join(r.mention for r in managed_roles),
                    ephemeral=True
                )

        await self.bot.welcome_engine.save(interaction.guild_id, auto_role_ids=[r.id for r in selected_roles])
        await interaction.response.send_message(
            '✅ Auto-assign roles updated: ' + (', '.join(r.mention for r in selected_roles) if selected_roles else 'Cleared all.'),
            ephemeral=True
        )

    @group.command(name='reset', description='Reset greeting options back to default settings')
    @app_commands.guild_only()
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def reset(self, interaction: discord.Interaction, kind: str):
        defaults = {
            f'{kind}_enabled': True,
            f'{kind}_channel_id': None,
            f'{kind}_message': f'Welcome {{mention}} to {{server}}!',
            f'{kind}_embed_title': f'Welcome to {{server}}',
            f'{kind}_embed_enabled': True,
            f'{kind}_embed_color': 0x5865F2,
            f'{kind}_image_url': '',
            f'{kind}_show_thumbnail': True,
            f'{kind}_show_footer': True,
            f'{kind}_footer_text': 'User ID: {user_id}'
        }
        await self._save(interaction.guild_id, **defaults)
        await interaction.response.send_message(f'🔄 Reset **{kind.title()}** configuration to default settings.', ephemeral=True)

    @group.command(name='status', description='View complete greeting configuration status')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def status(self, interaction: discord.Interaction):
        cfg = await self.bot.guild_config.get(interaction.guild_id)
        settings = await self.bot.welcome_engine.get(interaction.guild_id, cfg)

        w_id = cfg.get('welcome_channel_id')
        g_id = cfg.get('goodbye_channel_id')

        welcome_channel = interaction.guild.get_channel(w_id) if w_id and interaction.guild else None
        goodbye_channel = interaction.guild.get_channel(g_id) if g_id and interaction.guild else None

        welcome_fmt = welcome_channel.mention if welcome_channel else (f"<#{w_id}>" if w_id else "Disabled")
        goodbye_fmt = goodbye_channel.mention if goodbye_channel else (f"<#{g_id}>" if g_id else "Disabled")

        guild_name = interaction.guild.name if interaction.guild else "Server"

        embed = discord.Embed(
            title=f"⚙️ Greeting Configuration - {guild_name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Welcome Channel", value=welcome_fmt, inline=True)
        embed.add_field(name="Goodbye Channel", value=goodbye_fmt, inline=True)
        embed.add_field(name="Engine State", value="Active" if settings.get('enabled') else "Inactive", inline=True)

        embed.add_field(
            name="Welcome Image/GIF",
            value=f"`{cfg.get('welcome_image_url', 'None Set')}`",
            inline=False
        )
        embed.add_field(
            name="Goodbye Image/GIF",
            value=f"`{cfg.get('goodbye_image_url', 'None Set')}`",
            inline=False
        )

        auto_roles = [f"<@&{rid}>" for rid in settings.get('auto_role_ids', [])]
        embed.add_field(name="Auto Roles", value=", ".join(auto_roles) if auto_roles else "None", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Greeting(bot))
