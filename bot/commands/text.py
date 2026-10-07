"""Prefix/text equivalents for the complete user-facing slash command surface.

Default prefix: `,` (configurable with COMMAND_PREFIX).
Friendly reaction commands return GIFs; administrative commands remain permission
checked and use the same service/database layer as their slash counterparts.
"""
from __future__ import annotations
import random
from datetime import timedelta
import discord
from discord.ext import commands
from sqlalchemy import text
from bot.commands.fun import SAFE_ACTIONS
from bot.services.music import MusicError
from bot.ui import error_embed, info_embed, success_embed, warning_embed

class TextCommands(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @staticmethod
    def _can_act(ctx, member):
        if not ctx.guild or member == ctx.author or member == ctx.guild.owner: return False
        me=ctx.guild.me
        return bool(me and ctx.author.top_role > member.top_role and me.top_role > member.top_role)
    async def _gif(self, ctx, action, member=None):
        target = member or ctx.author
        key, emoji, verb = SAFE_ACTIONS[action]
        url = await self.bot.reactions.get(key) if key else None
        description = f'{ctx.author.mention} {verb} themselves!' if target.id == ctx.author.id else f'{ctx.author.mention} {verb} {target.mention}!'
        embed = info_embed(f'{emoji} {action.title()}', description)
        if url: embed.set_image(url=url)
        embed.set_footer(text='Fallen • Fun & community • Prefix: ,')
        await ctx.send(embed=embed)

    @commands.command(name="kill")
    async def kill(self,ctx,member:discord.Member): await self._gif(ctx,'kill',member)
    @commands.command(name="hug", aliases=["Hug"])
    async def hug(self,ctx,member:discord.Member): await self._gif(ctx,'hug',member)
    @commands.command(name="highfive")
    async def highfive(self,ctx,member:discord.Member): await self._gif(ctx,'highfive',member)
    @commands.command(name="pat")
    async def pat(self,ctx,member:discord.Member): await self._gif(ctx,'pat',member)
    @commands.command(name="poke")
    async def poke(self,ctx,member:discord.Member): await self._gif(ctx,'poke',member)
    @commands.command(name="bonk")
    async def bonk(self,ctx,member:discord.Member): await self._gif(ctx,'bonk',member)
    @commands.command(name="wave")
    async def wave(self,ctx,member:discord.Member): await self._gif(ctx,'wave',member)
    @commands.command(name="dance")
    async def dance(self,ctx,member:discord.Member=None): await self._gif(ctx,'dance',member)
    @commands.command(name="smile")
    async def smile(self,ctx,member:discord.Member=None): await self._gif(ctx,'smile',member)
    @commands.command(name="cry")
    async def cry(self,ctx,member:discord.Member=None): await self._gif(ctx,'cry',member)
    @commands.command(name="shrug")
    async def shrug(self,ctx,member:discord.Member=None): await self._gif(ctx,'shrug',member)
    @commands.command(name="sleep")
    async def sleep(self,ctx,member:discord.Member=None): await self._gif(ctx,'sleep',member)
    @commands.command(name="boop")
    async def boop(self,ctx,member:discord.Member): await self._gif(ctx,'boop',member)
    @commands.command(name="tickle")
    async def tickle(self,ctx,member:discord.Member): await self._gif(ctx,'tickle',member)
    @commands.command(name="punch")
    async def punch(self,ctx,member:discord.Member): await self._gif(ctx,'punch',member)
    @commands.command(name="slap")
    async def slap(self,ctx,member:discord.Member): await self._gif(ctx,'slap',member)
    @commands.command(name="bite")
    async def bite(self,ctx,member:discord.Member): await self._gif(ctx,'bite',member)
    @commands.command(name="hold")
    async def hold(self,ctx,member:discord.Member): await self._gif(ctx,'hold',member)
    @commands.command(name="attack")
    async def attack(self,ctx,member:discord.Member): await self._gif(ctx,'attack',member)
    @commands.command(name="shoot")
    async def shoot(self,ctx,member:discord.Member): await self._gif(ctx,'shoot',member)
    @commands.command(name="bully")
    async def bully(self,ctx,member:discord.Member): await self._gif(ctx,'bully',member)
    @commands.command(name="pout")
    async def pout(self,ctx,member:discord.Member=None): await self._gif(ctx,'pout',member)
    @commands.command(name="blush")
    async def blush(self,ctx,member:discord.Member=None): await self._gif(ctx,'blush',member)
    @commands.command(name="fuck")
    async def fuck(self,ctx,member:discord.Member=None): await self._gif(ctx,'fuck',member)

    @commands.command(name='uwuify')
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def uwuify(self, ctx, member: discord.Member, enabled: bool = True):
        if member.bot:
            return await ctx.send('❌ Bot messages are ignored by UwUify.')
        await self.bot.uwuify.set_enabled(ctx.guild.id, member.id, enabled)
        await ctx.send(f'✨ Real-time UwUify **{"enabled" if enabled else "disabled"}** for {member.mention}.')


    @commands.command(name="invites")
    @commands.guild_only()
    async def text_invites(self,ctx,member:discord.Member=None):
        m=member or ctx.author; rows=await self.bot.invites.stats(ctx.guild.id,m.id); joins=rows[0].joins if rows else 0
        await ctx.send(f"📨 {m.mention} has **{joins}** tracked invite joins.")

    @commands.command(name="inviteleaderboard", aliases=["invite-leaderboard"])
    @commands.guild_only()
    async def text_inviteleaderboard(self,ctx):
        rows=await self.bot.invites.stats(ctx.guild.id)
        if not rows: return await ctx.send('No invite joins have been tracked yet.')
        await ctx.send('🏆 **Invite Leaderboard**\n'+'\n'.join(f'**{n}.** <@{r.user_id}> — **{r.joins}** joins' for n,r in enumerate(rows[:10],1)))

    # Slash-style grouped prefix commands (kept alongside the short aliases).
    @commands.group(name='config', invoke_without_command=True)
    @commands.guild_only()
    async def config_group(self,ctx):
        if ctx.invoked_subcommand is None: await ctx.send(f'Use `{ctx.prefix}config autorole|logs|automod`.')
    @config_group.command(name='autorole')
    @commands.has_permissions(manage_guild=True)
    async def config_autorole(self,ctx,role:discord.Role=None): await self.autorole.callback(self,ctx,role)
    @config_group.command(name='logs')
    @commands.has_permissions(manage_guild=True)
    async def config_logs(self,ctx,channel:discord.TextChannel=None): await self.logs.callback(self,ctx,channel)
    @config_group.command(name='automod')
    @commands.has_permissions(manage_guild=True)
    async def config_automod(self,ctx,enabled:bool,spam_limit:int=6,window:int=8):
        if not 3<=spam_limit<=20 or not 2<=window<=60:return await ctx.send('❌ spam_limit must be 3–20 and window 2–60 seconds.')
        await self._set_cfg(ctx,'automod_enabled',enabled,f'🛡️ AutoMod: **{enabled}** ({spam_limit}/{window}s)')
        async with self.bot.db.session() as s:
            await s.execute(text('UPDATE guild_configs SET spam_limit=:l, spam_window=:w WHERE guild_id=:g'),{'l':spam_limit,'w':window,'g':ctx.guild.id}); await s.commit()
        await self.bot.guild_config.invalidate(ctx.guild.id)

    @commands.group(name='settings', invoke_without_command=True)
    @commands.guild_only()
    async def settings_group(self,ctx):
        if ctx.invoked_subcommand is None: await ctx.send(f'Use `{ctx.prefix}settings welcome-channel|goodbye-channel|automod|autorole`.')
    @settings_group.command(name='welcome-channel')
    @commands.has_permissions(manage_guild=True)
    async def settings_welcome(self,ctx,channel:discord.TextChannel): await self.welcome_channel.callback(self,ctx,channel)
    @settings_group.command(name='goodbye-channel')
    @commands.has_permissions(manage_guild=True)
    async def settings_goodbye(self,ctx,channel:discord.TextChannel): await self.goodbye_channel.callback(self,ctx,channel)
    @settings_group.command(name='automod')
    @commands.has_permissions(manage_guild=True)
    async def settings_automod(self,ctx,enabled:bool): await self.automod.callback(self,ctx,enabled)
    @settings_group.command(name='autorole')
    @commands.has_permissions(manage_guild=True)
    async def settings_autorole(self,ctx,role:discord.Role=None): await self.autorole.callback(self,ctx,role)

    @commands.group(name='greeting', aliases=['greet'], invoke_without_command=True)
    @commands.guild_only()
    async def greeting_group(self,ctx):
        if ctx.invoked_subcommand is None: await ctx.send(f'Use `{ctx.prefix}greeting channel|message|banner|embed|dm|button|details|status|placeholders|preset|mode|roles|log|security|button-set|advanced|test`.')
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
            error=Greeting._validate_template(message)
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
            f'Buttons: {len([b for b in settings.get("buttons",[]) if b.get("enabled")})}/5\n'
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

    @commands.group(name='custom', invoke_without_command=True)
    @commands.guild_only()
    async def custom_group(self,ctx):
        if ctx.invoked_subcommand is None: await ctx.send(f'Use `{ctx.prefix}custom set|remove`.')
    @custom_group.command(name='set')
    @commands.has_permissions(manage_guild=True)
    async def custom_group_set(self,ctx,name,*,response): await self.custom_set.callback(self,ctx,name,response=response)
    @custom_group.command(name='remove')
    @commands.has_permissions(manage_guild=True)
    async def custom_group_remove(self,ctx,name): await self.custom_remove.callback(self,ctx,name)

    @commands.group(name='engage', invoke_without_command=True)
    async def engage_group(self,ctx):
        if ctx.invoked_subcommand is None: await ctx.send(f'Use `{ctx.prefix}engage poll|8ball|choose`.')
    @engage_group.command(name='poll')
    async def engage_poll(self,ctx,*,question): await self.poll.callback(self,ctx,question=question)
    @engage_group.command(name='8ball')
    async def engage_8ball(self,ctx,*,question): await self.eightball.callback(self,ctx,question=question)
    @engage_group.command(name='choose')
    async def engage_choose(self,ctx,*,options): await self.choose.callback(self,ctx,options=options)

    @commands.group(name='security', invoke_without_command=True)
    @commands.guild_only()
    async def security_group(self,ctx):
        if ctx.invoked_subcommand is None: await ctx.send(f'Use `{ctx.prefix}security raid-status|lockdown|unlockdown`.')
    @security_group.command(name='raid-status')
    @commands.has_permissions(manage_guild=True)
    async def security_raid(self,ctx): await self.raid_status.callback(self,ctx)
    @security_group.command(name='lockdown')
    @commands.has_permissions(administrator=True)
    async def security_lock(self,ctx): await self.lockdown.callback(self,ctx)
    @security_group.command(name='unlockdown')
    @commands.has_permissions(administrator=True)
    async def security_unlock(self,ctx): await self.unlockdown.callback(self,ctx)

    # Moderation
    @commands.command(name='warn')
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def warn(self,ctx,member:discord.Member,*,reason='No reason provided'):
        if not self._can_act(ctx,member): return await ctx.send(embed=error_embed('Action blocked','Role hierarchy prevents that action.'))
        await self.bot.moderation.warn(ctx.guild.id,member.id,ctx.author.id,reason)
        try: await self.bot.platform.case(ctx.guild.id,member.id,ctx.author.id,'warn',reason)
        except Exception: self.bot.log.exception('failed to create prefix moderation case')
        count=await self.bot.moderation.count(ctx.guild.id,member.id)
        e=warning_embed('Member warned',f'{member.mention} has received a moderation warning.')
        e.add_field(name='Reason',value=reason[:1024],inline=False); e.add_field(name='Active warnings',value=f'`{count}`')
        await ctx.send(embed=e)
    @commands.command(name='warnings', aliases=['warns'])
    @commands.guild_only()
    async def warnings(self,ctx,member:discord.Member):
        rows=await self.bot.moderation.warnings(ctx.guild.id,member.id)
        await ctx.send(embed=discord.Embed(title=f'Warnings • {member}',description='\n'.join(f'`#{r.id}` <@{r.moderator_id}> — {r.reason}' for r in rows) or 'No warnings.'))
    @commands.command(name="mute", aliases=["m", "Mute"])
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def timeout(self,ctx,member:discord.Member,minutes:int=10,*,reason='No reason provided'):
        if not 1 <= minutes <= 10080: return await ctx.send('❌ Duration must be 1–10080 minutes.')
        if not self._can_act(ctx,member): return await ctx.send(embed=error_embed('Action blocked','Role hierarchy prevents that action.'))
        await member.timeout(discord.utils.utcnow()+timedelta(minutes=minutes),reason=reason)
        try: await self.bot.platform.case(ctx.guild.id,member.id,ctx.author.id,'timeout',reason)
        except Exception: self.bot.log.exception('failed to create prefix moderation case')
        e=success_embed('Member timed out',f'{member.mention} was timed out successfully.')
        e.add_field(name='Duration',value=f'`{minutes}` minutes'); e.add_field(name='Reason',value=reason[:1024],inline=False)
        await ctx.send(embed=e)
    @commands.command(name="timeout")
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def timeout_command(self,ctx,member:discord.Member,minutes:int=10,*,reason='No reason provided'):
        if not 1 <= minutes <= 10080: return await ctx.send('❌ Duration must be 1–10080 minutes.')
        if not self._can_act(ctx,member): return await ctx.send(embed=error_embed('Action blocked','Role hierarchy prevents that action.'))
        await member.timeout(discord.utils.utcnow()+timedelta(minutes=minutes),reason=reason)
        try: await self.bot.platform.case(ctx.guild.id,member.id,ctx.author.id,'timeout',reason)
        except Exception: self.bot.log.exception('failed to create prefix moderation case')
        e=success_embed('Member timed out',f'{member.mention} was timed out successfully.')
        e.add_field(name='Duration',value=f'`{minutes}` minutes'); e.add_field(name='Reason',value=reason[:1024],inline=False)
        await ctx.send(embed=e)

    @commands.command(name="unmute", aliases=["un", "Unmute"])
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def unmute(self,ctx,member:discord.Member):
        if not self._can_act(ctx,member): return await ctx.send(embed=error_embed('Action blocked','Role hierarchy prevents that action.'))
        await member.timeout(None,reason=f'Unmuted by {ctx.author}'); await ctx.send(embed=success_embed('Member unmuted',f'{member.mention} is no longer timed out.'))
    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(self,ctx,member:discord.Member,*,reason='No reason provided'):
        if not self._can_act(ctx,member): return await ctx.send(embed=error_embed('Action blocked','Role hierarchy prevents that action.'))
        await member.ban(reason=reason)
        try: await self.bot.platform.case(ctx.guild.id,member.id,ctx.author.id,'ban',reason)
        except Exception: self.bot.log.exception('failed to create prefix moderation case')
        await ctx.send(embed=success_embed('Member banned',f'{member.mention} was banned successfully.'))
    @commands.command(name='kick')
    @commands.has_permissions(kick_members=True)
    @commands.guild_only()
    async def kick(self,ctx,member:discord.Member,*,reason='No reason provided'):
        if not self._can_act(ctx,member): return await ctx.send(embed=error_embed('Action blocked','Role hierarchy prevents that action.'))
        await member.kick(reason=reason)
        try: await self.bot.platform.case(ctx.guild.id,member.id,ctx.author.id,'kick',reason)
        except Exception: self.bot.log.exception('failed to create prefix moderation case')
        await ctx.send(embed=success_embed('Member kicked',f'{member.mention} was kicked successfully.'))
    @commands.command(name='clear')
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def clear(self,ctx,amount:int):
        if not 1 <= amount <= 100: return await ctx.send('❌ Amount must be 1–100.')
        deleted=await ctx.channel.purge(limit=amount+1); await ctx.send(f'🧹 Deleted {max(0,len(deleted)-1)} messages.',delete_after=5)
    @commands.command(name='slowmode')
    @commands.has_permissions(manage_channels=True)
    @commands.guild_only()
    async def slowmode(self,ctx,seconds:int):
        if not 0 <= seconds <= 21600:return await ctx.send('❌ Seconds must be 0–21600.')
        await ctx.channel.edit(slowmode_delay=seconds); await ctx.send(f'🐢 Slowmode set to {seconds}s.')
    @commands.command(name='lock')
    @commands.has_permissions(manage_channels=True)
    @commands.guild_only()
    async def lock(self,ctx):
        from bot.ui import success_embed
        await ctx.channel.set_permissions(ctx.guild.default_role,send_messages=False,reason=f'Lock by {ctx.author}')
        await ctx.send(embed=success_embed('Channel locked', f'{ctx.channel.mention} is now locked for @everyone.'))
    @commands.command(name='unlock')
    @commands.has_permissions(manage_channels=True)
    @commands.guild_only()
    async def unlock(self,ctx):
        from bot.ui import success_embed
        await ctx.channel.set_permissions(ctx.guild.default_role,send_messages=None,reason=f'Unlock by {ctx.author}')
        await ctx.send(embed=success_embed('Channel unlocked', f'{ctx.channel.mention} has returned to inherited permissions.'))

    # Utility/community
    @commands.command(name='ping')
    async def ping(self,ctx):
        e=info_embed('🏓 Pong!', 'Fallen is online and responding.')
        e.add_field(name='Gateway',value=f'`{self.bot.latency*1000:.0f} ms`'); e.add_field(name='Prefix',value='`,`')
        await ctx.send(embed=e)
    @commands.command(name='health')
    async def health(self,ctx):
        db=await self.bot.db.health(); redis=await self.bot.cache.health()
        e=success_embed('System healthy','All core dependencies are responding.') if db and redis else error_embed('Degraded services','At least one core dependency is unavailable.')
        e.add_field(name='PostgreSQL',value='🟢 Online' if db else '🔴 Offline'); e.add_field(name='Redis',value='🟢 Online' if redis else '🔴 Offline'); await ctx.send(embed=e)
    @commands.command(name='level')
    @commands.guild_only()
    async def level(self,ctx,member:discord.Member=None):
        member=member or ctx.author
        row=await self.bot.levels.get(ctx.guild.id,member.id)
        level=row.level if row else 0; xp=row.xp if row else 0
        await ctx.send(f'🏆 {member.mention}: level **{level}**, XP **{xp}/{self.bot.levels.xp_needed(level)}**.')

    @commands.command(name='level-channel')
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def level_channel(self,ctx,channel:discord.TextChannel):
        me=ctx.guild.me
        if me is None:
            return await ctx.send('❌ I cannot resolve my server member.')
        permissions=channel.permissions_for(me)
        missing=[name for name,ok in (('View Channel',permissions.view_channel),('Send Messages',permissions.send_messages),('Embed Links',permissions.embed_links)) if not ok]
        if missing:
            return await ctx.send(f'❌ I cannot use {channel.mention}. Missing: **{", ".join(missing)}**.')
        await self.bot.levels.update_settings(ctx.guild.id,announcement_channel_id=channel.id,announce=True)
        await ctx.send(f'✅ Level-up announcements will now be sent only in {channel.mention}.')

    @commands.command(name='level-channel-reset')
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def level_channel_reset(self,ctx):
        await self.bot.levels.update_settings(ctx.guild.id,announcement_channel_id=None)
        await ctx.send('✅ Dedicated level-up channel disabled. Announcements use the channel where the level-up happened.')

    @commands.command(name='level-xp-channel')
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def level_xp_channel(self,ctx,channel:discord.TextChannel):
        await self.bot.levels.update_settings(ctx.guild.id,xp_channels=[channel.id])
        await ctx.send(f'✅ XP is now earned only in {channel.mention}.')

    @commands.command(name='level-xp-channel-reset')
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def level_xp_channel_reset(self,ctx):
        await self.bot.levels.update_settings(ctx.guild.id,xp_channels=[])
        await ctx.send('✅ XP channel restriction removed. XP can be earned in all eligible channels.')

    @commands.group(name='levelrole', invoke_without_command=True)
    @commands.guild_only()
    async def levelrole_group(self,ctx):
        if ctx.invoked_subcommand is None: await ctx.send(f'Use `{ctx.prefix}levelrole add <level> @role`, `{ctx.prefix}levelrole remove <level>`, or `{ctx.prefix}levelrole list`.')

    @levelrole_group.command(name='add')
    @commands.has_permissions(manage_roles=True)
    async def levelrole_add(self,ctx,level:int,role:discord.Role):
        if level < 1 or role.is_default() or role.managed or role >= ctx.guild.me.top_role: return await ctx.send('❌ Invalid level or role. The role must be below my highest role.')
        await self.bot.levels.set_role(ctx.guild.id,level,role.id); await ctx.send(f'✅ Level **{level}** now awards {role.mention}.')

    @levelrole_group.command(name='remove')
    @commands.has_permissions(manage_roles=True)
    async def levelrole_remove(self,ctx,level:int):
        await self.bot.levels.remove_role(ctx.guild.id,level); await ctx.send(f'✅ Removed the level **{level}** role reward.')

    @levelrole_group.command(name='list')
    async def levelrole_list(self,ctx):
        rows=await self.bot.levels.configured_roles(ctx.guild.id)
        await ctx.send('🎖️ **Level Roles**\n'+'\n'.join(f'Level **{r.level}** → <@&{r.role_id}>' for r in rows) if rows else 'No level roles are configured.')
    @commands.command(name='serverinfo')
    @commands.guild_only()
    async def serverinfo(self,ctx):
        g=ctx.guild; e=discord.Embed(title=g.name,color=discord.Color.blurple()); e.add_field(name='Members',value=str(g.member_count)); e.add_field(name='Channels',value=str(len(g.channels))); e.add_field(name='Roles',value=str(len(g.roles)))
        if g.icon:e.set_thumbnail(url=g.icon.url)
        await ctx.send(embed=e)
    @commands.command(name='avatar')
    async def avatar(self,ctx,member:discord.Member=None):
        m=member or ctx.author; e=discord.Embed(title=f'{m.display_name} avatar'); e.set_image(url=m.display_avatar.url); await ctx.send(embed=e)

    # Engagement
    @commands.command(name='poll')
    async def poll(self,ctx,*,question):
        e=discord.Embed(title='📊 Poll',description=question,color=discord.Color.blurple()); m=await ctx.send(embed=e); await m.add_reaction('👍'); await m.add_reaction('👎')
    @commands.command(name='8ball', aliases=['eightball'])
    async def eightball(self,ctx,*,question): await ctx.send(f'🎱 {random.choice(("Yes.","No.","Maybe.","Ask again later.","Definitely."))}')
    @commands.command(name='choose')
    async def choose(self,ctx,*,options):
        vals=[x.strip() for x in options.split('|') if x.strip()]
        await ctx.send('Give at least two options separated by `|`.' if len(vals)<2 else f'🎯 I choose **{random.choice(vals)}**')

    # Economy/platform
    @commands.command(name='balance')
    @commands.guild_only()
    async def balance(self,ctx): await ctx.send(f'💰 Balance: **{await self.bot.platform.balance(ctx.guild.id,ctx.author.id)}**')
    @commands.command(name='daily')
    @commands.guild_only()
    async def daily(self,ctx):
        from bot.ui import success_embed, error_embed
        allowed=await self.bot.limiter.allow(f'daily:{ctx.guild.id}:{ctx.author.id}',1,86400)
        if not allowed:
            return await ctx.send(embed=error_embed('Daily already claimed','You can claim the reward again after the cooldown resets.'))
        b=await self.bot.platform.change_balance(ctx.guild.id,ctx.author.id,100)
        await ctx.send(embed=success_embed('Daily reward', f'You received **100 coins**. Your balance is now **{b:,}**.'))
    @commands.command(name='coinflip')
    async def coinflip(self,ctx): await ctx.send(f'🪙 **{random.choice(("Heads","Tails"))}**')
    @commands.command(name='case')
    @commands.guild_only()
    async def case(self,ctx,member:discord.Member):
        rows=await self.bot.platform.cases(ctx.guild.id,member.id); await ctx.send(embed=discord.Embed(title=f'Cases • {member}',description='\n'.join(f'`#{r.id}` **{r.action}** — {r.reason} (<@{r.moderator_id}>)' for r in rows) or 'No cases found.'))
    @commands.command(name='remind')
    @commands.guild_only()
    async def remind(self,ctx,seconds:int,*,message):
        if not 1<=seconds<=2592000:return await ctx.send('❌ Seconds must be 1–2592000.')
        await self.bot.platform.add_reminder(ctx.guild.id,ctx.author.id,ctx.channel.id,seconds,message); await ctx.send(f'⏰ Reminder set for {seconds} seconds.')
    @commands.command(name='suggest')
    @commands.guild_only()
    async def suggest(self,ctx,*,content):
        row=await self.bot.platform.suggestion(ctx.guild.id,ctx.author.id,ctx.channel.id,ctx.message.id,content); await ctx.send(f'✅ Suggestion #{row.id} submitted.')

    # Tickets/music
    @commands.command(name="play", aliases=["p", "Play"])
    @commands.guild_only()
    async def play(self,ctx,*,query):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send('Join a voice channel before requesting music.')
        try:
            count, title = await self.bot.music.play(ctx.guild, ctx.author.voice.channel, query)
        except MusicError as exc:
            return await ctx.send(str(exc))
        if count == 1:
            await ctx.send(f'Now playing **{title}**.')
        else:
            await ctx.send(f'Added **{count} tracks** from **{title}** to the queue.')

    @commands.command(name="stop", aliases=["s", "Stop"])
    @commands.guild_only()
    async def stop(self,ctx):
        changed = await self.bot.music.stop(ctx.guild)
        await ctx.send('Stopped playback and cleared the queue.' if changed else 'There is no active player.')

    @commands.command(name='skip')
    @commands.guild_only()
    async def skip(self,ctx):
        changed = await self.bot.music.skip(ctx.guild)
        await ctx.send('Skipped the current track.' if changed else 'Nothing is playing.')

    @commands.command(name='pause')
    @commands.guild_only()
    async def pause(self,ctx):
        changed = await self.bot.music.pause(ctx.guild)
        await ctx.send('Playback paused.' if changed else 'Nothing is playing.')

    @commands.command(name='resume')
    @commands.guild_only()
    async def resume(self,ctx):
        changed = await self.bot.music.resume(ctx.guild)
        await ctx.send('Playback resumed.' if changed else 'Playback is not paused.')

    @commands.command(name='queue')
    @commands.guild_only()
    async def queue(self,ctx):
        tracks = self.bot.music.queue(ctx.guild.id)
        if not tracks:
            return await ctx.send('The queue is empty.')
        lines = [f'{index}. [{track.title}]({track.uri})' for index, track in enumerate(tracks[:10], 1)]
        await ctx.send('\n'.join(lines))

    @commands.command(name='ticket')
    @commands.guild_only()
    async def ticket(self,ctx):
        ch=await self.bot.tickets.create(ctx.guild,None,ctx.author); await ch.send(f'🎫 Welcome {ctx.author.mention}. Staff can help you here.'); await ctx.send(f'Created {ch.mention}.')
    @commands.command(name='close')
    @commands.guild_only()
    async def close_ticket(self,ctx):
        if not ctx.channel.name.startswith('ticket-'):return await ctx.send('This is not a ticket channel.')
        await ctx.send('Closing ticket…'); await ctx.channel.delete(reason='Ticket closed')
    @commands.command(name='music-status')
    async def music_status(self,ctx):
        node = self.bot.music.node
        message = f'Music node **{node.identifier}** is connected.' if node else 'Music is offline. Configure a reachable Lavalink v4 node.'
        await ctx.send(message)
    # Security
    @commands.command(name='raid-status')
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def raid_status(self,ctx): await ctx.send(f'🚨 Recent joins tracked: **{await self.bot.cache.anti_raid_count(ctx.guild.id,10,8)}**')
    @commands.command(name='lockdown')
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def lockdown(self,ctx):
        changed=await self.bot.security_lockdown(ctx.guild.id, reason=f'Lockdown by {ctx.author}')
        await ctx.send(embed=success_embed('Server locked',f'Locked **{changed}** text channels. The previous state is stored for restoration.'))
    @commands.command(name='unlockdown')
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def unlockdown(self,ctx):
        changed=await self.bot.security_unlockdown(ctx.guild.id, reason=f'Unlockdown by {ctx.author}')
        await ctx.send(embed=success_embed('Server unlocked',f'Restored **{changed}** text channels from the saved lockdown state.'))

    @commands.command(name='levelrole-remove')
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def levelrole_remove_command(self,ctx,level:int): await self.bot.levels.remove_role(ctx.guild.id,level); await ctx.send(f'✅ Removed level **{level}** role reward.')

    @commands.command(name='levelroles')
    @commands.guild_only()
    async def levelroles(self,ctx):
        rows=await self.bot.levels.configured_roles(ctx.guild.id)
        await ctx.send('🎖️ **Level Roles**\n'+('\n'.join(f'Level **{r.level}** → <@&{r.role_id}>' for r in rows) if rows else 'None configured.'))


    # Configuration/settings aliases
    @commands.command(name='welcome-channel')
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def welcome_channel(self,ctx,channel:discord.TextChannel): await self._set_cfg(ctx,'welcome_channel_id',channel.id,f'✅ Welcome channel: {channel.mention}')
    @commands.command(name='goodbye-channel')
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def goodbye_channel(self,ctx,channel:discord.TextChannel): await self._set_cfg(ctx,'goodbye_channel_id',channel.id,f'✅ Goodbye channel: {channel.mention}')
    async def _set_cfg(self,ctx,col,value,msg):
        await self.bot.guild_config.update(ctx.guild.id, **{col: value})
        await ctx.send(msg)
    @commands.command(name='autorole')
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def autorole(self,ctx,role:discord.Role=None): await self._set_cfg(ctx,'autorole_id',role.id if role else None,f'🎭 Autorole: {role.mention if role else "disabled"}')
    @commands.command(name='automod')
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def automod(self,ctx,enabled:bool): await self._set_cfg(ctx,'automod_enabled',enabled,f'🛡️ AutoMod: **{enabled}**')
    @commands.command(name='logs')
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def logs(self,ctx,channel:discord.TextChannel=None): await self._set_cfg(ctx,'log_channel_id',channel.id if channel else None,f'📝 Log channel: {channel.mention if channel else "disabled"}')
    @commands.command(name='custom-set')
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def custom_set(self,ctx,name,*,response): await self.bot.custom_commands.set(ctx.guild.id,name.lower().replace(' ','-')[:64],response[:1900]); await ctx.send(f'Custom command `{name}` saved.')
    @commands.command(name='custom-remove')
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def custom_remove(self,ctx,name): await self.bot.custom_commands.remove(ctx.guild.id,name.lower()); await ctx.send('Removed.')

async def setup(bot): await bot.add_cog(TextCommands(bot))
