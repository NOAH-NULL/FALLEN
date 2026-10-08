"""Dedicated prefix commands for FALLEN's welcome/goodbye system.

These commands intentionally live outside TextCommands so unrelated prefix
command failures cannot disable the welcomer configuration interface.
"""

from __future__ import annotations

import discord
from discord.ext import commands

from bot.commands.greeting import validate_template


class GreetingPrefix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _set_cfg(self, ctx, key, value, message):
        await self.bot.guild_config.update(ctx.guild.id, **{key: value})
        await ctx.send(message)

    @commands.group(name='greeting', aliases=['greet'], invoke_without_command=True)
    @commands.guild_only()
    async def greeting_group(self,ctx):
        if ctx.invoked_subcommand is None: await ctx.send(f'Use `{ctx.prefix}greet channel|message|banner|embed|dm|button|details|status|placeholders|preset|mode|roles|log|security|button-set|bots|reliability|advanced|test|welcome|goodbye`.')
    @greeting_group.command(name='channel')
    @commands.has_permissions(manage_guild=True)
    async def greeting_channel(self,ctx,kind:str,channel:discord.TextChannel):
        if kind not in ('welcome','goodbye'): return await ctx.send('kind must be welcome or goodbye')
        await self._set_cfg(ctx,f'{kind}_channel_id',channel.id,f'✅ {kind.title()} channel: {channel.mention}')
    @greeting_group.command(name='message')
    @commands.has_permissions(manage_guild=True)
    async def greeting_message(self,ctx,kind:str,*,message):
        if kind not in ('welcome','goodbye'): return await ctx.send('kind must be welcome or goodbye')
        await self._set_cfg(ctx,f'{kind}_message',message[:1000],'✅ Greeting message saved.')
    @greeting_group.command(name='banner')
    @commands.has_permissions(manage_guild=True)
    async def greeting_banner(self,ctx,kind:str,attachment:discord.Attachment=None,*,url:str=None):
        if kind not in ('welcome','goodbye'): return await ctx.send('kind must be welcome or goodbye')
        if attachment:
            try:
                data=self.bot.greetings.validate_upload(await attachment.read(),attachment.content_type)
            except ValueError as exc:
                return await ctx.send(f'❌ {exc}')
            await self.bot.guild_config.update(ctx.guild.id,**{f'{kind}_background':f'assets/{kind}.gif',f'{kind}_background_data':data})
        elif url and url.strip().startswith(('https://','http://')):
            await self.bot.guild_config.update(ctx.guild.id,**{f'{kind}_background':url.strip()[:2000],f'{kind}_background_data':None})
        else:
            return await ctx.send('❌ Attach an image/GIF or provide an http(s) image URL.')
        await ctx.send(f'✅ Custom {kind} banner saved. GIFs remain animated.')
    @greeting_group.command(name='banner-reset')
    @commands.has_permissions(manage_guild=True)
    async def greeting_banner_reset(self,ctx,kind:str):
        if kind not in ('welcome','goodbye'): return await ctx.send('kind must be welcome or goodbye')
        await self.bot.guild_config.update(ctx.guild.id,**{f'{kind}_background':f'assets/{kind}.gif',f'{kind}_background_data':None})
        await ctx.send(f'✅ {kind.title()} banner reset to default.')

    @greeting_group.command(name='embed')
    @commands.has_permissions(manage_guild=True)
    async def greeting_embed(self,ctx,kind:str,enabled:bool,title:str=None,*,description:str=None):
        if kind not in ('welcome','goodbye'): return await ctx.send('kind must be welcome or goodbye')
        await self._set_cfg(ctx,f'{kind}_embed_enabled',enabled,f'✅ {kind.title()} embed: **{enabled}**')
        if title is not None: await self._set_cfg(ctx,f'{kind}_embed_title',title[:256], '✅ Embed title saved.')
        if description is not None: await self._set_cfg(ctx,f'{kind}_embed_description',description[:4096], '✅ Embed description saved.')
        await ctx.send('The embed will be sent alongside the banner/GIF.')

    @greeting_group.command(name='status')
    @commands.has_permissions(manage_guild=True)
    async def greeting_status(self,ctx):
        cfg=await self.bot.guild_config.get(ctx.guild.id)
        settings=await self.bot.welcome_engine.get(ctx.guild.id,cfg)
        welcome=ctx.guild.get_channel(cfg.get('welcome_channel_id')) if cfg.get('welcome_channel_id') else None
        goodbye=ctx.guild.get_channel(cfg.get('goodbye_channel_id')) if cfg.get('goodbye_channel_id') else None
        buttons=[b for b in settings.get('buttons',[]) if b.get('enabled')]
        roles=[f"<@&{rid}>" for rid in settings.get('auto_role_ids',[])]
        await ctx.send(
            '**Welcome Engine status**\n'
            f'Welcome: {welcome.mention if welcome else "not configured"}\n'
            f'Goodbye: {goodbye.mention if goodbye else "not configured"}\n'
            f'Engine: {settings.get("enabled")} • preset={settings.get("preset","full")}\n'
            f'Public: {settings.get("public_enabled")} • DM: {settings.get("dm_enabled")}\n'
            f'Auto roles: {", ".join(roles) if roles else "none"}\n'
            f'Security: threshold={settings.get("new_account_days",7)}d • alerts={settings.get("alert_new_accounts")}\n'
            f'Buttons: {len(buttons)}/5 • details={settings.get("show_details")}\n'
            f'Retry: {settings.get("retry_attempts",2)} public + {settings.get("dm_retry",1)} DM • dedupe={settings.get("dedupe_seconds",90)}s'
        )
    @greeting_group.command(name='placeholders')
    @commands.has_permissions(manage_guild=True)
    async def greeting_placeholders(self,ctx):
        await ctx.send(
            '**Greeting placeholders**\n'
            '`{mention}` `{name}` `{username}` `{server}` `{count}` `{membercount}`\n'
            '`{inviter}` `{inviter_name}` `{invites}` `{account_age}`\n'
            '`{account_created}` `{joined_at}` `{boosts}` `{server_id}` `{user_id}`'
        )

    @greeting_group.command(name='dm')
    @commands.has_permissions(manage_guild=True)
    async def greeting_dm(self,ctx,enabled:bool,*,message:str=None):
        if message is not None:
            from bot.commands.greeting import Greeting
            error=validate_template(message)
            if error: return await ctx.send(f'❌ {error}')
        values={'welcome_dm_enabled':enabled}
        if message is not None: values['welcome_dm_message']=message[:1900]
        await self.bot.guild_config.update(ctx.guild.id,**values)
        await self.bot.welcome_engine.save(ctx.guild.id,dm_enabled=enabled)
        await ctx.send(f'✅ Welcome DMs are now **{"enabled" if enabled else "disabled"}**.')

    @greeting_group.command(name='button')
    @commands.has_permissions(manage_guild=True)
    async def greeting_button(self,ctx,enabled:bool,url:str=None,*,label:str='Read the Rules'):
        if enabled and (not url or not url.strip().startswith('https://')):
            return await ctx.send('❌ The button requires a valid **https://** URL.')
        if label and len(label)>80: label=label[:80]
        values={'welcome_button_enabled':enabled}
        if url is not None: values['welcome_button_url']=url.strip()[:2000]
        if label: values['welcome_button_label']=label.strip()
        await self.bot.guild_config.update(ctx.guild.id,**values)
        settings=await self.bot.welcome_engine.get(ctx.guild.id)
        buttons=list(settings.get('buttons') or [])
        while len(buttons)<5:
            buttons.append({'enabled':False,'label':'Open','url':'https://discord.com/'})
        buttons[0]={'enabled':enabled,'label':(label or settings.get('welcome_button_label') or 'Read the Rules').strip()[:80],'url':(url or settings.get('welcome_button_url') or 'https://discord.com/').strip()[:2000]}
        await self.bot.welcome_engine.save(ctx.guild.id,buttons=buttons)
        await ctx.send(f'✅ Welcome button **{"enabled" if enabled else "disabled"}**.')

    @greeting_group.command(name='details')
    @commands.has_permissions(manage_guild=True)
    async def greeting_details(self,ctx,enabled:bool):
        await self.bot.guild_config.update(ctx.guild.id,welcome_show_details=enabled)
        await self.bot.welcome_engine.save(ctx.guild.id,show_details=enabled)
        await ctx.send(f'✅ Welcome detail fields **{"enabled" if enabled else "disabled"}**.')

    @greeting_group.command(name='preset')
    @commands.has_permissions(manage_guild=True)
    async def greeting_preset(self,ctx,preset:str):
        preset=preset.lower().strip()
        if preset not in {'minimal','onboarding','security','full'}:
            return await ctx.send('❌ Preset must be: minimal, onboarding, security, or full.')
        settings=await self.bot.welcome_engine.get(ctx.guild.id)
        presets={
            'minimal': {'enabled':True,'public_enabled':True,'dm_enabled':False,'show_details':True,'show_risk':False,'alert_new_accounts':False,'log_enabled':False,'auto_role_ids':[],'buttons':[]},
            'onboarding': {'enabled':True,'public_enabled':True,'dm_enabled':True,'show_details':True,'show_risk':True,'alert_new_accounts':False,'log_enabled':False},
            'security': {'enabled':True,'public_enabled':True,'dm_enabled':True,'show_details':True,'show_risk':True,'alert_new_accounts':True,'log_enabled':True,'new_account_days':14},
            'full': {'enabled':True,'public_enabled':True,'dm_enabled':True,'show_details':True,'show_risk':True,'alert_new_accounts':True,'log_enabled':True,'new_account_days':7},
        }
        settings.update(presets[preset]); settings['preset']=preset
        await self.bot.guild_config.update(ctx.guild.id,welcome_settings=self.bot.welcome_engine.normalize(settings))
        await ctx.send(f'✅ Welcome Engine preset set to **{preset}**.')

    @greeting_group.command(name='mode')
    @commands.has_permissions(manage_guild=True)
    async def greeting_mode(self,ctx,public:bool,dm:bool):
        if not public and not dm:
            return await ctx.send('❌ At least one of public or DM delivery must be enabled.')
        await self.bot.welcome_engine.save(ctx.guild.id,public_enabled=public,dm_enabled=dm)
        await ctx.send(f'✅ Welcome delivery: public={public}, DM={dm}.')

    @greeting_group.command(name='roles')
    @commands.has_permissions(manage_guild=True)
    async def greeting_roles(self,ctx,role1:discord.Role=None,role2:discord.Role=None,role3:discord.Role=None,role4:discord.Role=None,role5:discord.Role=None):
        roles=[r for r in (role1,role2,role3,role4,role5) if r]
        me=ctx.guild.me
        if me:
            invalid=[r for r in roles if r>=me.top_role]
            if invalid:
                return await ctx.send('❌ I cannot assign: '+', '.join(r.mention for r in invalid))
        await self.bot.welcome_engine.save(ctx.guild.id,auto_role_ids=[r.id for r in roles])
        await ctx.send('✅ Welcome auto-roles: '+(', '.join(r.mention for r in roles) if roles else 'cleared'))

    @greeting_group.command(name='log')
    @commands.has_permissions(manage_guild=True)
    async def greeting_log(self,ctx,enabled:bool,channel:discord.TextChannel=None):
        if enabled and channel is None:
            return await ctx.send('❌ Choose a log channel when enabling security alerts.')
        if enabled:
            me=ctx.guild.me; permissions=channel.permissions_for(me) if me else None
            if not permissions or not permissions.send_messages or not permissions.embed_links:
                return await ctx.send(f'❌ I cannot send embeds in {channel.mention}.')
        await self.bot.welcome_engine.save(ctx.guild.id,log_enabled=enabled,log_channel_id=channel.id if channel else None)
        await ctx.send(f'✅ Welcome security log {"enabled" if enabled else "disabled"}.')

    @greeting_group.command(name='security')
    @commands.has_permissions(manage_guild=True)
    async def greeting_security(self,ctx,new_account_days:int,alert_new_accounts:bool):
        if not 0<=new_account_days<=3650:
            return await ctx.send('❌ New-account threshold must be between 0 and 3650 days.')
        await self.bot.welcome_engine.save(ctx.guild.id,new_account_days=new_account_days,alert_new_accounts=alert_new_accounts,show_risk=True)
        await ctx.send(f'✅ New-account detection: {new_account_days} days, alerts={alert_new_accounts}.')

    @greeting_group.command(name='button-set')
    @commands.has_permissions(manage_guild=True)
    async def greeting_button_set(self,ctx,slot:int,enabled:bool,url:str=None,*,label:str=None):
        if not 1<=slot<=5:
            return await ctx.send('❌ Button slot must be between 1 and 5.')
        settings=await self.bot.welcome_engine.get(ctx.guild.id)
        buttons=list(settings.get('buttons') or [])
        while len(buttons)<5:
            buttons.append({'enabled':False,'label':'Open','url':'https://discord.com/'})
        if enabled and (not url or not url.strip().startswith('https://')):
            return await ctx.send('❌ An enabled link button requires an https:// URL.')
        if label is not None and not label.strip():
            return await ctx.send('❌ Button label cannot be empty.')
        idx=slot-1
        buttons[idx]={
            'enabled':enabled,
            'label':(label or buttons[idx].get('label') or 'Open').strip()[:80],
            'url':(url or buttons[idx].get('url') or 'https://discord.com/').strip()[:2000],
        }
        await self.bot.welcome_engine.save(ctx.guild.id,buttons=buttons)
        await ctx.send(f'✅ Welcome button slot {slot} {"enabled" if enabled else "disabled"}.')

    @greeting_group.command(name='bots')
    @commands.has_permissions(manage_guild=True)
    async def greeting_bots(self,ctx,enabled:bool):
        await self.bot.welcome_engine.save(ctx.guild.id,include_bots=enabled)
        await ctx.send(f'✅ Welcome messages for bot accounts are now **{"enabled" if enabled else "disabled"}**.')

    @greeting_group.command(name='reliability')
    @commands.has_permissions(manage_guild=True)
    async def greeting_reliability(self,ctx,retry_attempts:int,dm_retry:int,dedupe_seconds:int):
        if not 0<=retry_attempts<=4 or not 0<=dm_retry<=2 or not 0<=dedupe_seconds<=600:
            return await ctx.send('❌ Values out of range: public retries 0-4, DM retries 0-2, duplicate window 0-600s.')
        await self.bot.welcome_engine.save(ctx.guild.id,retry_attempts=retry_attempts,dm_retry=dm_retry,dedupe_seconds=dedupe_seconds)
        await ctx.send(f'✅ Reliability tuned: public retries={retry_attempts}, DM retries={dm_retry}, duplicate window={dedupe_seconds}s.')

    @greeting_group.command(name='advanced')
    @commands.has_permissions(manage_guild=True)
    async def greeting_advanced(self,ctx):
        settings=await self.bot.welcome_engine.get(ctx.guild.id)
        await ctx.send(
            '**Welcome Engine 2.0**\n'
            f'Preset: {settings.get("preset","custom")}\n'
            f'Public: {settings.get("public_enabled")} • DM: {settings.get("dm_enabled")}\n'
            f'New-account threshold: {settings.get("new_account_days")}d\n'
            f'Auto-roles: {len(settings.get("auto_role_ids",[]))}\n'
            f'Buttons: {len([b for b in settings.get("buttons",[]) if b.get("enabled")])}/5\n'
            f'Retries: {settings.get("retry_attempts")} / DM {settings.get("dm_retry")}\n'
            f'Dedupe: {settings.get("dedupe_seconds")}s'
        )

    @greeting_group.command(name='test')
    @commands.has_permissions(manage_guild=True)
    async def greeting_test(self,ctx,kind:str='welcome'):
        kind=kind.lower().strip()
        if kind not in ('welcome','goodbye'):
            return await ctx.send('❌ kind must be `welcome` or `goodbye`.')
        cfg=await self.bot.guild_config.get(ctx.guild.id)
        require_embed=bool(cfg.get(f'{kind}_embed_enabled',True))
        me=ctx.guild.me
        if me is None:
            return await ctx.send('❌ I cannot resolve my server member.')
        permissions=ctx.channel.permissions_for(me)
        missing=[name for name,ok in (
            ('View Channel',permissions.view_channel),
            ('Send Messages',permissions.send_messages),
            ('Attach Files',permissions.attach_files),
            ('Embed Links',permissions.embed_links if require_embed else True),
        ) if not ok]
        if missing:
            return await ctx.send(f'❌ I am missing: **{", ".join(missing)}** in {ctx.channel.mention}.')
        try:
            await self.bot.greeting_worker.deliver(
                ctx.author,
                kind,
                force_channel=ctx.channel,
            )
        except ValueError as exc:
            return await ctx.send(f'❌ Greeting test failed: `{exc}`.')
        except discord.Forbidden:
            return await ctx.send('❌ Discord denied the greeting send. Check my channel permissions.')
        except discord.HTTPException as exc:
            self.bot.log.warning(
                'prefix greeting test failed guild=%s kind=%s status=%s',
                ctx.guild.id, kind, getattr(exc,'status','?')
            )
            return await ctx.send('❌ Discord rejected the greeting test (`' + str(getattr(exc,'status','unknown')) + '`).')
        except Exception:
            self.bot.log.exception(
                'prefix greeting test crashed guild=%s kind=%s user=%s',
                ctx.guild.id, kind, ctx.author.id
            )
            return await ctx.send('❌ Greeting test failed unexpectedly. Check the bot logs.')
        await ctx.send(f'✅ {kind.title()} test sent successfully.')

    @greeting_group.command(name='welcome')
    @commands.has_permissions(manage_guild=True)
    async def greeting_welcome_test(self,ctx):
        await self.greeting_test.callback(self,ctx,'welcome')

    @greeting_group.command(name='goodbye')
    @commands.has_permissions(manage_guild=True)
    async def greeting_goodbye_test(self,ctx):
        await self.greeting_test.callback(self,ctx,'goodbye')

async def setup(bot):
    await bot.add_cog(GreetingPrefix(bot))
