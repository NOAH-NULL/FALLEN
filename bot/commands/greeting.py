import discord
from discord import app_commands
from discord.ext import commands
import string


KIND_CHOICES = [
    app_commands.Choice(name='Welcome', value='welcome'),
    app_commands.Choice(name='Goodbye', value='goodbye'),
]


class Greeting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    group = app_commands.Group(name='greeting', description='Configure welcome and goodbye')

    async def _save(self, guild_id, **values):
        await self.bot.guild_config.update(guild_id, **values)

    @staticmethod
    def _validate_template(value: str):
        if not value or not value.strip():
            return 'Message cannot be empty.'
        allowed = {
            'mention', 'name', 'username', 'server', 'count',
            'membercount', 'inviter', 'inviter_name', 'invites',
            'account_age', 'account_created', 'joined_at',
            'boosts', 'server_id', 'user_id',
        }
        try:
            for _, field_name, _, _ in string.Formatter().parse(value):
                if field_name and field_name not in allowed:
                    return f'Unknown template variable: {{{field_name}}}.'
        except ValueError:
            return 'Invalid braces in the message template.'
        try:
            value.format(
                mention='@user',
                name='Member',
                username='member',
                server='Server',
                count=1,
                membercount=1,
                inviter='Unknown',
                inviter_name='Unknown',
                invites=0,
                account_age='1d',
                account_created='2026-01-01',
                joined_at='2026-01-01',
                boosts=0,
                server_id=0,
                user_id=0,
            )
        except (KeyError, ValueError, IndexError):
            return 'Invalid message template.'
        return None

    @staticmethod
    def _can_send(channel, me, require_embed=True):
        if me is None:
            return False, 'View Server Member'
        permissions = channel.permissions_for(me)
        missing = []
        if not permissions.view_channel:
            missing.append('View Channel')
        if not permissions.send_messages:
            missing.append('Send Messages')
        if not permissions.attach_files:
            missing.append('Attach Files')
        if require_embed and not permissions.embed_links:
            missing.append('Embed Links')
        return (not missing, ', '.join(missing))

    @group.command(name='channel')
    @app_commands.guild_only()
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def channel(self, i, kind: str, channel: discord.TextChannel):
        if kind not in ('welcome', 'goodbye'):
            return await i.response.send_message('kind must be welcome or goodbye', ephemeral=True)
        me = i.guild.me
        if me is None:
            return await i.response.send_message('❌ I cannot resolve my server member.', ephemeral=True)
        permissions = channel.permissions_for(me)
        missing = [
            name for name, ok in (
                ('View Channel', permissions.view_channel),
                ('Send Messages', permissions.send_messages),
                ('Attach Files', permissions.attach_files),
                ('Embed Links', permissions.embed_links if True else True),
            ) if not ok
        ]
        if missing:
            return await i.response.send_message(
                f'❌ I cannot use {channel.mention}. Missing: **{", ".join(missing)}**.',
                ephemeral=True,
            )
        await self._save(i.guild_id, **{f'{kind}_channel_id': channel.id})
        await i.response.send_message(f'✅ {kind.title()} channel set to {channel.mention}.')

    @group.command(name='message')
    @app_commands.guild_only()
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def message(self, i, kind: str, text_value: str):
        if kind not in ('welcome', 'goodbye'):
            return await i.response.send_message('kind must be welcome or goodbye', ephemeral=True)
        error = self._validate_template(text_value)
        if error:
            return await i.response.send_message(f'❌ {error}', ephemeral=True)
        await self._save(i.guild_id, **{f'{kind}_message': text_value[:1000]})
        await i.response.send_message(f'{kind.title()} message saved.')

    @group.command(name='banner')
    @app_commands.guild_only()
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def banner(self, i, kind: str, attachment: discord.Attachment = None, url: str = None):
        if kind not in ('welcome', 'goodbye'):
            return await i.response.send_message('kind must be welcome or goodbye', ephemeral=True)
        if attachment:
            try:
                data = self.bot.greetings.validate_upload(await attachment.read(), attachment.content_type)
            except ValueError as exc:
                return await i.response.send_message(str(exc), ephemeral=True)
            await self._save(
                i.guild_id,
                **{f'{kind}_background': f'assets/{kind}.gif', f'{kind}_background_data': data},
            )
        elif url and url.strip().startswith(('https://', 'http://')):
            await self._save(
                i.guild_id,
                **{f'{kind}_background': url.strip()[:2000], f'{kind}_background_data': None},
            )
        else:
            return await i.response.send_message('Upload an image/GIF or provide an image URL.', ephemeral=True)
        await i.response.send_message(f'Custom {kind} banner saved. GIFs remain animated.')

    @group.command(name='status')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def status(self, i):
        cfg = await self.bot.guild_config.get(i.guild_id)
        welcome_channel = i.guild.get_channel(cfg.get('welcome_channel_id')) if cfg.get('welcome_channel_id') else None
        goodbye_channel = i.guild.get_channel(cfg.get('goodbye_channel_id')) if cfg.get('goodbye_channel_id') else None
        lines = [
            f"**Welcome:** {welcome_channel.mention if welcome_channel else 'Not configured'}",
            f"**Goodbye:** {goodbye_channel.mention if goodbye_channel else 'Not configured'}",
            f"**Welcome DM:** {'Enabled' if cfg.get('welcome_dm_enabled') else 'Disabled'}",
            f"**Rules button:** {'Enabled' if cfg.get('welcome_button_enabled') else 'Disabled'}",
            f"**Details:** {'Enabled' if cfg.get('welcome_show_details', True) else 'Disabled'}",
            f"**Welcome embed:** {'Enabled' if cfg.get('welcome_embed_enabled', True) else 'Disabled'}",
            f"**Goodbye embed:** {'Enabled' if cfg.get('goodbye_embed_enabled', True) else 'Disabled'}",
        ]
        if cfg.get('welcome_button_enabled'):
            lines.append(f"**Button:** `{(cfg.get('welcome_button_label') or 'Read the Rules')[:80]}` → {cfg.get('welcome_button_url') or 'Invalid/unset URL'}")
        await i.response.send_message('\n'.join(lines), ephemeral=True)

    @group.command(name='placeholders')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def placeholders(self, i):
        await i.response.send_message(
            '**Greeting placeholders**\n'
            '`{mention}` `{name}` `{username}` `{server}` `{count}` `{membercount}`\n'
            '`{inviter}` `{inviter_name}` `{invites}` `{account_age}`\n'
            '`{account_created}` `{joined_at}` `{boosts}` `{server_id}` `{user_id}`',
            ephemeral=True,
        )

    @group.command(name='dm')
    @app_commands.guild_only()
    @app_commands.choices(kind=[app_commands.Choice(name='Welcome', value='welcome')])
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(enabled='Send a private welcome DM when someone joins', message='DM template using greeting placeholders')
    async def dm(self, i, kind: str, enabled: bool, message: str = None):
        error = self._validate_template(message) if message is not None else None
        if error:
            return await i.response.send_message(f'❌ {error}', ephemeral=True)
        values = {'welcome_dm_enabled': enabled}
        if message is not None:
            values['welcome_dm_message'] = message[:1900]
        await self._save(i.guild_id, **values)
        state = 'enabled' if enabled else 'disabled'
        await i.response.send_message(
            f'✅ Welcome DMs are now **{state}**.' + (' The DM template was updated.' if message is not None else ''),
            ephemeral=True,
        )

    @group.command(name='button')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(enabled='Show a link button on the welcome message', url='HTTPS URL for rules, website, verification, etc.', label='Button label')
    async def button(self, i, enabled: bool, url: str = None, label: str = None):
        if enabled:
            if not url or not url.strip().startswith('https://'):
                return await i.response.send_message('❌ The button requires a valid **https://** URL.', ephemeral=True)
            if label is not None and not label.strip():
                return await i.response.send_message('❌ Button label cannot be empty.', ephemeral=True)
        values = {'welcome_button_enabled': enabled}
        if url is not None:
            values['welcome_button_url'] = url.strip()[:2000]
        if label is not None:
            values['welcome_button_label'] = label.strip()[:80]
        await self._save(i.guild_id, **values)
        state = 'enabled' if enabled else 'disabled'
        await i.response.send_message(f'✅ Welcome button **{state}**.', ephemeral=True)

    @group.command(name='details')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(enabled='Show member/account/inviter details in the welcome embed')
    async def details(self, i, enabled: bool):
        await self._save(i.guild_id, welcome_show_details=enabled)
        state = 'enabled' if enabled else 'disabled'
        await i.response.send_message(f'✅ Welcome detail fields **{state}**.', ephemeral=True)
    @group.command(name='banner-reset')
    @app_commands.guild_only()
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def banner_reset(self, i, kind: str):
        if kind not in ('welcome', 'goodbye'):
            return await i.response.send_message('kind must be welcome or goodbye', ephemeral=True)
        await self._save(
            i.guild_id,
            **{f'{kind}_background': f'assets/{kind}.gif', f'{kind}_background_data': None},
        )
        await i.response.send_message(f'{kind.title()} banner reset to the default.')

    @group.command(name='embed')
    @app_commands.guild_only()
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(kind='welcome or goodbye', enabled='Show the embed alongside the banner', title='Embed title', description='Embed description', color='Hex color such as #5865F2')
    async def embed(self, i, kind: str, enabled: bool, title: str = None, description: str = None, color: str = None):
        if kind not in ('welcome', 'goodbye'):
            return await i.response.send_message('kind must be welcome or goodbye', ephemeral=True)
        values = {f'{kind}_embed_enabled': enabled}
        if title is not None:
            values[f'{kind}_embed_title'] = title[:256]
        if description is not None:
            error = self._validate_template(description)
            if error:
                return await i.response.send_message(f'❌ {error}', ephemeral=True)
            values[f'{kind}_embed_description'] = description[:4096]
        if color is not None:
            try:
                value = int(color.strip().lstrip('#'), 16)
            except ValueError:
                return await i.response.send_message('Color must be hex, e.g. #5865F2.', ephemeral=True)
            if not 0 <= value <= 0xFFFFFF:
                return await i.response.send_message('Color must be between #000000 and #FFFFFF.', ephemeral=True)
            values[f'{kind}_embed_color'] = value
        await self._save(i.guild_id, **values)
        await i.response.send_message(f'{kind.title()} embed updated. The banner/GIF and embed will be sent together.')

    async def _run_test(self, guild, channel, member, kind):
        if kind not in ('welcome', 'goodbye'):
            return False, 'kind must be welcome or goodbye'

        cfg = await self.bot.guild_config.get(guild.id)
        require_embed = bool(cfg.get(f'{kind}_embed_enabled', True))

        me = guild.me
        if me is None and self.bot.user is not None:
            me = guild.get_member(self.bot.user.id)

        ok, missing = self._can_send(channel, me, require_embed=require_embed)
        if not ok:
            return False, f'I am missing: **{missing}** in {channel.mention}.'

        try:
            await self.bot.greeting_worker.deliver(
                member,
                kind,
                force_channel=channel,
            )
        except ValueError as exc:
            self.bot.log.warning(
                'greeting test rejected guild=%s kind=%s user=%s: %s',
                guild.id, kind, member.id, exc,
            )
            return False, f'Greeting test failed: `{exc}`.'
        except discord.Forbidden:
            self.bot.log.warning(
                'greeting test forbidden guild=%s kind=%s user=%s',
                guild.id, kind, member.id,
            )
            return False, 'Greeting test failed: Discord denied the send. Check View Channel, Send Messages, Attach Files, and Embed Links permissions.'
        except discord.HTTPException as exc:
            self.bot.log.warning(
                'greeting test HTTP failure guild=%s kind=%s user=%s status=%s',
                guild.id, kind, member.id, getattr(exc, 'status', '?'),
            )
            return False, 'Greeting test failed: Discord HTTP error `' + str(getattr(exc, 'status', 'unknown')) + '`.'
        except Exception:
            self.bot.log.exception(
                'greeting test crashed guild=%s kind=%s user=%s',
                guild.id, kind, member.id,
            )
            return False, 'Greeting test failed unexpectedly. The full error is in the bot logs.'

        return True, f'✅ {kind.title()} test sent successfully.'

    @group.command(name='test')
    @app_commands.guild_only()
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def test(self, i, kind: str = 'welcome'):
        await i.response.defer(ephemeral=True)
        ok, message = await self._run_test(
            i.guild,
            i.channel,
            i.user,
            kind.lower(),
        )
        await i.followup.send(
            message if ok else f'❌ {message}',
            ephemeral=True,
        )



async def setup(bot):
    await bot.add_cog(Greeting(bot))
