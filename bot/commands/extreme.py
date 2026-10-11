from __future__ import annotations
import io, json
from datetime import timedelta
import discord
from discord.ext import commands
from bot.services.extreme import FEATURES, IMPLEMENTED_FEATURES

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
        enabled = sum(bool(state.get(name, False)) for name in IMPLEMENTED_FEATURES)
        await ctx.send(
            f'⚙️ **Fallen V16:** `{enabled}/{len(IMPLEMENTED_FEATURES)}` implemented capabilities enabled. '
            f'The catalog contains 100 entries; unfinished entries cannot be enabled yet. '
            f'Use `{ctx.prefix}v16 help` or `/v16 help`.'
        )

    @v16.command(name='help', description='Show V16 capability domains')
    async def help_cmd(self, ctx):
        state = await self.bot.extreme.get(ctx.guild.id)
        lines = []
        for category, names in FEATURES.items():
            supported = [name for name in names if name in IMPLEMENTED_FEATURES]
            active = sum(1 for name in supported if state.get(name, False))
            catalog_only = len(names) - len(supported)
            suffix = f' · {catalog_only} catalog-only' if catalog_only else ''
            lines.append(f'**{category.title()}** — {active}/{len(supported)} enabled{suffix}')
        await ctx.send('\n'.join(lines))

    @v16.command(name='status', description='Show V16 capability status')
    async def status(self, ctx):
        state=await self.bot.extreme.get(ctx.guild.id)
        active = [key for key in IMPLEMENTED_FEATURES if state.get(key, False)]
        await ctx.send(
            f'**{len(active)}/{len(IMPLEMENTED_FEATURES)} implemented capabilities enabled**\n'
            + (', '.join(f'`{name}`' for name in sorted(active)) if active else 'No optional capabilities enabled.')
            + '\nCatalog-only entries are unavailable until implemented.'
        )

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
        name = name.strip()
        if not name or len(name) > 64 or name.startswith("__") or any(ch not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_- ' for ch in name):
            return await ctx.send('❌ Snapshot names must be 1–64 characters using letters, numbers, spaces, `_` or `-`; names starting with `__` are reserved for internal recovery data.')
        data=await self.bot.extreme.snapshot(ctx.guild.id)
        await self.bot.extreme.snapshot_save(ctx.guild.id,ctx.author.id,name,data)
        raw=json.dumps(data,indent=2).encode()
        await ctx.send(f'✅ Snapshot `{name}` saved.', file=discord.File(io.BytesIO(raw),filename=f'{name}.json'), allowed_mentions=discord.AllowedMentions.none())

    @v16.command(name='restore', description='Restore a named feature configuration snapshot')
    @commands.has_guild_permissions(administrator=True)
    async def restore(self, ctx, name: str = 'default'):
        row=await self.bot.extreme.snapshot_get(ctx.guild.id,name)
        if not row: return await ctx.send(f'❌ Snapshot `{name}` does not exist.')
        features = row.payload.get('features', {})
        try:
            result = await self.bot.extreme.restore_features(ctx.guild.id, features)
        except ValueError as exc:
            return await ctx.send(f'❌ {exc}')
        skipped = result['skipped']
        detail = f" Restored {result['restored']} supported feature(s)."
        if skipped:
            detail += f" Skipped {len(skipped)} unsupported or malformed feature(s)."
        await ctx.send(f'✅ Restored `{name}`.' + detail)

    @v16.command(
        name='security-backup',
        description='Refresh the trusted channel and role recovery baseline',
    )
    @commands.has_guild_permissions(administrator=True)
    async def security_backup(self, ctx):
        await self.bot.snapshot_security_state(ctx.guild, ctx.author.id)
        await ctx.send(
            '✅ Security recovery baseline refreshed from the current server state. '
            'Only run this when the server configuration is trusted; this replaces the previous baseline.'
        )

    @v16.command(name='security-log', description='Show the recent security timeline')
    @commands.has_guild_permissions(manage_guild=True)
    async def security_log(self, ctx, limit: int = 15):
        rows=await self.bot.extreme.security_events(ctx.guild.id,max(1,min(limit,25)))
        if not rows: return await ctx.send('No security events recorded.')
        lines=[f'`#{r.id}` **{r.event_type}** actor={r.actor_id or "system"} target={r.target_id or "-"}' for r in rows]
        await ctx.send('\n'.join(lines))

    @v16.command(name='unlockdown', description='Restore saved channel permissions after lockdown')
    @commands.has_guild_permissions(administrator=True)
    async def unlockdown(self, ctx):
        snapshot = await self.bot.extreme.snapshot_get(ctx.guild.id, '__lockdown__')
        if not snapshot:
            return await ctx.send('No saved lockdown recovery snapshot exists.')
        changed = await self.bot.security_unlockdown(
            ctx.guild.id,
            reason=f'Manual lockdown recovery by {ctx.author.id}',
        )
        remaining = await self.bot.extreme.snapshot_get(ctx.guild.id, '__lockdown__')
        if remaining:
            return await ctx.send(
                f'⚠️ Restored permissions in {changed} channel(s), but some updates failed. '
                'The recovery snapshot was kept; run this command again after checking bot permissions.'
            )
        await ctx.send(f'✅ Lockdown recovery completed for {changed} channel(s).')

    @v16.command(name='unquarantine', description='Restore a quarantined member\'s saved roles')
    @commands.has_guild_permissions(administrator=True)
    async def unquarantine(self, ctx, member: discord.Member):
        snapshot_name = f'__quarantine__:{member.id}'
        if not await self.bot.extreme.snapshot_get(ctx.guild.id, snapshot_name):
            return await ctx.send('No saved quarantine recovery data exists for that member.')
        restored = await self.bot.restore_quarantined_member(ctx.guild, member.id)
        remaining = await self.bot.extreme.snapshot_get(ctx.guild.id, snapshot_name)
        if remaining:
            return await ctx.send(
                f'⚠️ Restored {restored} role(s), but recovery is incomplete. '
                'The quarantine role and recovery snapshot were kept; check role hierarchy and bot permissions.'
            )
        await ctx.send(f'✅ Quarantine recovery completed; restored {restored} role(s).')

    @v16.command(name='automod-rule', description='Create/update a regex or domain AutoMod rule')
    @commands.has_guild_permissions(manage_guild=True)
    async def automod_rule(self, ctx, name: str, kind: str, pattern: str, action: str='delete'):
        kind=kind.lower()
        if kind not in {'regex','domain_blacklist','domain_whitelist'}: return await ctx.send('❌ kind must be `regex`, `domain_blacklist`, or `domain_whitelist`.')
        if action not in {'delete','warn','log'}: return await ctx.send('❌ action must be `delete`, `warn`, or `log`.')
        try:
            await self.bot.extreme.upsert_automod_rule(ctx.guild.id, name, kind, pattern, action)
        except ValueError as exc:
            return await ctx.send(f'❌ {exc}')
        except Exception:
            self.bot.log.exception('V16 AutoMod rule save failed guild=%s rule=%s', ctx.guild.id, name)
            return await ctx.send('❌ Could not save the AutoMod rule because of an internal error. Check the bot logs.')
        await ctx.send(f'✅ AutoMod rule `{name}` saved.', allowed_mentions=discord.AllowedMentions.none())

    @v16.command(name='profile', description='Set a persistent member profile bio')
    async def profile(self, ctx, *, bio: str=''):
        if not await self.bot.extreme.enabled(ctx.guild.id,'member_profiles'): return await ctx.send('❌ Member profiles are disabled.')
        if len(bio)>500: return await ctx.send('❌ Bio must be 500 characters or fewer.')
        row=await self.bot.extreme.set_profile(ctx.guild.id,ctx.author.id,bio=bio)
        await ctx.send(f'👤 **{ctx.author.display_name}**\n{row.bio or "No bio set."}', allowed_mentions=discord.AllowedMentions.none())

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
        if member.bot:
            return await ctx.send('❌ Reputation can only be given to human members.')
        allowed = await self.bot.limiter.allow(
            f"v16-rep:{ctx.guild.id}:{ctx.author.id}:{member.id}",
            1,
            86400,
        )
        if not allowed:
            return await ctx.send('❌ You can give this member reputation only once every 24 hours.')
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
        await ctx.send(f'🎵 Saved playlist {name} with **{len(vals)}** tracks.', allowed_mentions=discord.AllowedMentions.none())

    @v16.command(name='playlist-list', description='List your saved playlists')
    async def playlist_list(self, ctx):
        if not await self.bot.extreme.enabled(ctx.guild.id, 'personal_playlists'):
            return await ctx.send('❌ Personal playlists are disabled. Enable the feature first.')
        rows = await self.bot.extreme.playlists(ctx.guild.id, ctx.author.id)
        if not rows:
            return await ctx.send('No playlists saved.')
        await ctx.send('\n'.join(f'🎵 {r.name} — {len(r.tracks)} tracks' for r in rows), allowed_mentions=discord.AllowedMentions.none())

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
            self.bot.log.exception(
                'temporary-ban expiry scheduling failed guild=%s member=%s',
                ctx.guild.id,
                member.id,
            )
            try:
                await ctx.guild.unban(
                    member,
                    reason='Rollback: temporary-ban scheduling failed',
                )
            except discord.HTTPException:
                self.bot.log.exception(
                    'temporary-ban rollback failed guild=%s member=%s; manual unban may be required',
                    ctx.guild.id,
                    member.id,
                )
                try:
                    await self.bot.extreme.record_security(
                        ctx.guild.id,
                        'temporary_ban_rollback_failed',
                        actor_id=ctx.author.id,
                        target_id=member.id,
                        details={'minutes': minutes, 'reason': reason[:400]},
                    )
                except Exception:
                    self.bot.log.exception(
                        'could not record temporary-ban rollback failure guild=%s member=%s',
                        ctx.guild.id,
                        member.id,
                    )
                return await ctx.send(
                    '❌ Expiry scheduling failed and automatic rollback also failed. '
                    'The member may still be banned; please verify and unban them manually if needed.'
                )
            return await ctx.send(
                '❌ Could not schedule the temporary ban expiry, so the ban was rolled back.'
            )
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
