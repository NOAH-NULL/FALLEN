from __future__ import annotations
import io, json
from datetime import timedelta
import discord
from discord.ext import commands
from bot.services.extreme import FEATURES

class Extreme(commands.Cog):
    """Single hybrid interface for the V16 capabilities.

    One implementation powers both `/v16 ...` and `,v16 ...`, eliminating the
    previous duplicated prefix/slash implementations.
    """
    def __init__(self, bot): self.bot = bot

    @commands.hybrid_group(name='v16', invoke_without_command=True, description='Configure Fallen V16 capabilities')
    @commands.guild_only()
    async def v16(self, ctx: commands.Context):
        state = await self.bot.extreme.get(ctx.guild.id)
        enabled = sum(bool(v) for v in state.values())
        await ctx.send(f'⚙️ **Fallen V16:** `{enabled}/100` capabilities enabled. Use `{ctx.prefix}v16 help` or `/v16 help`.')

    @v16.command(name='help', description='Show V16 capability domains')
    async def help_cmd(self, ctx):
        state = await self.bot.extreme.get(ctx.guild.id)
        lines = []
        for category, names in FEATURES.items():
            active = sum(1 for name in names if state.get(name, False))
            lines.append(f'**{category.title()}** — {active}/{len(names)}')
        await ctx.send('\n'.join(lines))

    @v16.command(name='status', description='Show V16 capability status')
    async def status(self, ctx):
        state=await self.bot.extreme.get(ctx.guild.id)
        active=[k for k,v in state.items() if v]
        await ctx.send(f'**{len(active)}/100 enabled**\n'+(', '.join(f'`{x}`' for x in active) if active else 'No optional capabilities enabled.'))

    @v16.command(name='set', description='Enable or disable a capability')
    @commands.has_guild_permissions(manage_guild=True)
    async def set_feature(self, ctx, feature: str, enabled: bool):
        try: await self.bot.extreme.set(ctx.guild.id,feature,enabled)
        except ValueError as exc: return await ctx.send(f'❌ {exc}')
        await ctx.send(f'✅ `{feature}` is now **{"enabled" if enabled else "disabled"}**.')

    @v16.command(name='validate', description='Validate persistent V16 configuration')
    @commands.has_guild_permissions(manage_guild=True)
    async def validate(self, ctx):
        errors=await self.bot.extreme.validate(ctx.guild.id)
        await ctx.send('✅ Configuration is valid.' if not errors else '❌\n'+'\n'.join(errors))

    @v16.command(name='snapshot', description='Save a named server configuration snapshot')
    @commands.has_guild_permissions(administrator=True)
    async def snapshot(self, ctx, name: str = 'default'):
        data=await self.bot.extreme.snapshot(ctx.guild.id)
        await self.bot.extreme.snapshot_save(ctx.guild.id,ctx.author.id,name,data)
        raw=json.dumps(data,indent=2).encode()
        await ctx.send(f'✅ Snapshot `{name}` saved.', file=discord.File(io.BytesIO(raw),filename=f'{name}.json'))

    @v16.command(name='restore', description='Restore a named feature configuration snapshot')
    @commands.has_guild_permissions(administrator=True)
    async def restore(self, ctx, name: str = 'default'):
        row=await self.bot.extreme.snapshot_get(ctx.guild.id,name)
        if not row: return await ctx.send(f'❌ Snapshot `{name}` does not exist.')
        features=row.payload.get('features',{})
        for key,value in features.items():
            if key in self.bot.extreme.all_names(): await self.bot.extreme.set(ctx.guild.id,key,bool(value))
        await ctx.send(f'✅ Restored `{name}`.')

    @v16.command(name='security-log', description='Show the recent security timeline')
    @commands.has_guild_permissions(manage_guild=True)
    async def security_log(self, ctx, limit: int = 15):
        rows=await self.bot.extreme.security_events(ctx.guild.id,max(1,min(limit,25)))
        if not rows: return await ctx.send('No security events recorded.')
        lines=[f'`#{r.id}` **{r.event_type}** actor={r.actor_id or "system"} target={r.target_id or "-"}' for r in rows]
        await ctx.send('\n'.join(lines))

    @v16.command(name='automod-rule', description='Create/update a regex or domain AutoMod rule')
    @commands.has_guild_permissions(manage_guild=True)
    async def automod_rule(self, ctx, name: str, kind: str, pattern: str, action: str='delete'):
        kind=kind.lower()
        if kind not in {'regex','domain_blacklist','domain_whitelist'}: return await ctx.send('❌ kind must be `regex`, `domain_blacklist`, or `domain_whitelist`.')
        if action not in {'delete','warn','log'}: return await ctx.send('❌ action must be `delete`, `warn`, or `log`.')
        try: await self.bot.extreme.upsert_automod_rule(ctx.guild.id,name,kind,pattern,action)
        except Exception as exc: return await ctx.send(f'❌ Could not save rule: {exc}')
        await ctx.send(f'✅ AutoMod rule `{name}` saved.')

    @v16.command(name='profile', description='Set a persistent member profile bio')
    async def profile(self, ctx, *, bio: str=''):
        if not await self.bot.extreme.enabled(ctx.guild.id,'member_profiles'): return await ctx.send('❌ Member profiles are disabled.')
        if len(bio)>500: return await ctx.send('❌ Bio must be 500 characters or fewer.')
        row=await self.bot.extreme.set_profile(ctx.guild.id,ctx.author.id,bio=bio)
        await ctx.send(f'👤 **{ctx.author.display_name}**\n{row.bio or "No bio set."}')

    @v16.command(name='reputation', description='Show a member reputation score')
    async def reputation(self, ctx, member: discord.Member | None = None):
        member=member or ctx.author; row=await self.bot.extreme.reputation(ctx.guild.id,member.id)
        await ctx.send(f'⭐ {member.mention} reputation: **{row.score if row else 0}**')

    @v16.command(name='rep', description='Give one reputation point to a member')
    async def rep(self, ctx, member: discord.Member):
        if not await self.bot.extreme.enabled(ctx.guild.id, 'server_reputation'):
            return await ctx.send('❌ Server reputation is disabled. Enable the feature first.')
        if member.id == ctx.author.id:
            return await ctx.send('❌ You cannot give reputation to yourself.')
        score = await self.bot.extreme.reputation_change(ctx.guild.id, member.id, 1)
        await ctx.send(f'⭐ {member.mention} now has **{score}** reputation.')

    @v16.command(name='playlist-save', description='Save a text-based playlist for later music integration')
    async def playlist_save(self, ctx, name: str, tracks: str):
        if not await self.bot.extreme.enabled(ctx.guild.id, 'personal_playlists'):
            return await ctx.send('❌ Personal playlists are disabled. Enable the feature first.')
        vals = [x.strip() for x in tracks.split('|') if x.strip()]
        if not vals:
            return await ctx.send('❌ Provide tracks separated by |.')
        await self.bot.extreme.save_playlist(ctx.guild.id, ctx.author.id, name, vals)
        await ctx.send(f'🎵 Saved playlist {name} with **{len(vals)}** tracks.')

    @v16.command(name='playlist-list', description='List your saved playlists')
    async def playlist_list(self, ctx):
        if not await self.bot.extreme.enabled(ctx.guild.id, 'personal_playlists'):
            return await ctx.send('❌ Personal playlists are disabled. Enable the feature first.')
        rows = await self.bot.extreme.playlists(ctx.guild.id, ctx.author.id)
        if not rows:
            return await ctx.send('No playlists saved.')
        await ctx.send('\n'.join(f'🎵 {r.name} — {len(r.tracks)} tracks' for r in rows))

    @v16.command(name='temp-timeout', description='Temporarily timeout a member')
    @commands.has_guild_permissions(moderate_members=True)
    async def temp_timeout(self, ctx, member: discord.Member, minutes: int, *, reason: str = 'Temporary timeout'):
        if not 1 <= minutes <= 10080:
            return await ctx.send('❌ Duration must be 1–10080 minutes.')
        if not await self.bot.extreme.enabled(ctx.guild.id, 'temporary_timeouts'):
            return await ctx.send('❌ Temporary timeouts are disabled. Enable the feature first.')
        if member >= ctx.guild.me:
            return await ctx.send('❌ I cannot moderate that member.')
        await member.timeout(
            discord.utils.utcnow() + timedelta(minutes=minutes),
            reason=reason[:512],
        )
        await ctx.send(f'⏱️ Timed out {member.mention} for **{minutes} minutes**.')

    @v16.command(name='temp-ban', description='Temporarily ban a member')
    @commands.has_guild_permissions(ban_members=True)
    async def temp_ban(self, ctx, member: discord.Member, minutes: int, *, reason: str = 'Temporary ban'):
        if not 1 <= minutes <= 43200:
            return await ctx.send('❌ Duration must be 1–43200 minutes.')
        if not await self.bot.extreme.enabled(ctx.guild.id, 'temporary_bans'):
            return await ctx.send('❌ Temporary bans are disabled. Enable the feature first.')
        if not await self.bot.extreme.enabled(ctx.guild.id, 'scheduled_punishments'):
            return await ctx.send('❌ Scheduled punishments are disabled, so a temporary ban cannot be auto-lifted safely.')
        if member >= ctx.guild.me:
            return await ctx.send('❌ I cannot moderate that member.')
        await member.ban(reason=reason[:512])
        try:
            await self.bot.extreme.schedule(
                ctx.guild.id,
                member.id,
                'ban',
                discord.utils.utcnow() + timedelta(minutes=minutes),
            )
        except Exception:
            try:
                await ctx.guild.unban(member, reason='Rollback: temporary-ban scheduling failed')
            except discord.HTTPException:
                pass
            raise
        await ctx.send(f'🔨 Temporarily banned **{member}** for **{minutes} minutes**.')

    @v16.command(name='ticket-note', description='Add a staff note to the current V16 ticket')
    @commands.has_guild_permissions(manage_channels=True)
    async def ticket_note(self, ctx, *, note: str):
        row=await self.bot.extreme.ticket_get(ctx.channel.id)
        if not row: return await ctx.send('❌ This is not a V16 ticket.')
        await self.bot.extreme.ticket_update(ctx.channel.id,notes=(row.notes+'\n'+note).strip())
        await ctx.send('📝 Ticket note saved.')

    @v16.command(name='ticket-claim', description='Claim the current V16 ticket')
    @commands.has_guild_permissions(manage_channels=True)
    async def ticket_claim(self, ctx):
        row=await self.bot.extreme.ticket_get(ctx.channel.id)
        if not row: return await ctx.send('❌ This is not a V16 ticket.')
        await self.bot.extreme.ticket_update(ctx.channel.id,claimer_id=ctx.author.id)
        await ctx.send(f'🎫 Ticket claimed by {ctx.author.mention}.')

    @v16.command(name='ticket-priority', description='Set the current ticket priority')
    @commands.has_guild_permissions(manage_channels=True)
    async def ticket_priority(self, ctx, priority: int):
        if not 0<=priority<=5:return await ctx.send('❌ Priority must be 0–5.')
        row=await self.bot.extreme.ticket_get(ctx.channel.id)
        if not row:return await ctx.send('❌ This is not a V16 ticket.')
        await self.bot.extreme.ticket_update(ctx.channel.id,priority=priority)
        await ctx.send(f'🎫 Ticket priority set to **{priority}**.')

async def setup(bot): await bot.add_cog(Extreme(bot))
