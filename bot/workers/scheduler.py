import asyncio, logging
import discord
log=logging.getLogger('bot.scheduler')
class Scheduler:
    def __init__(self,bot,interval=5): self.bot=bot; self.interval=interval; self.task=None; self.stop=asyncio.Event()
    async def start(self):
        if self.task and not self.task.done():
            return
        self.stop.clear()
        self.task=asyncio.create_task(self.run(), name='fallen-scheduler')
    async def run(self):
        while not self.stop.is_set():
            try:
                for r in await self.bot.platform.due_reminders():
                    ch=self.bot.get_channel(r.channel_id)
                    if ch is None:
                        try:
                            ch=await self.bot.fetch_channel(r.channel_id)
                        except discord.NotFound:
                            await self.bot.platform.complete_reminder(r.id)
                            log.warning('reminder channel deleted id=%s channel=%s; discarded', r.id, r.channel_id)
                            continue
                        except Exception:
                            await self.bot.platform.release_reminder(r.id)
                            log.exception('reminder channel lookup failed id=%s; will retry', r.id)
                            continue
                    try:
                        await ch.send(
                            f'⏰ <@{r.user_id}> {r.message}',
                            allowed_mentions=discord.AllowedMentions(
                                users=[discord.Object(id=r.user_id)],
                                roles=False,
                                everyone=False,
                                replied_user=False,
                            ),
                        )
                        await self.bot.platform.complete_reminder(r.id)
                    except discord.NotFound:
                        await self.bot.platform.complete_reminder(r.id)
                        log.warning('reminder target disappeared id=%s; discarded', r.id)
                    except Exception:
                        await self.bot.platform.release_reminder(r.id)
                        log.exception('reminder delivery failed id=%s; will retry', r.id)
                for action in await self.bot.extreme.due_actions():
                    guild=self.bot.get_guild(action.guild_id)
                    if not guild:
                        # A cache miss can be transient during startup or a
                        # shard reconnect. Completing a temporary-ban expiry
                        # here could leave the member banned indefinitely.
                        await self.bot.extreme.release_action(action.id)
                        log.warning(
                            'scheduled action guild unavailable id=%s guild=%s; released for retry',
                            action.id,
                            action.guild_id,
                        )
                        continue
                    try:
                        if action.action == 'timeout':
                            member = guild.get_member(action.target_id)
                            if not member:
                                await self.bot.extreme.complete_action(action.id)
                                log.warning('timeout target unavailable id=%s; completed as already gone', action.id)
                                continue
                            await member.timeout(None, reason='V16 temporary timeout expired')
                        elif action.action == 'ban':
                            # Banned users are commonly absent from the member cache.
                            await guild.unban(discord.Object(id=action.target_id), reason='V16 temporary ban expired')
                        else:
                            await self.bot.extreme.release_action(action.id)
                            log.warning('unknown scheduled action id=%s action=%s; released claim', action.id, action.action)
                            continue
                        await self.bot.extreme.complete_action(action.id)
                    except discord.NotFound:
                        # The desired end state is already true (e.g. an already
                        # unbanned user). Mark the action complete rather than retrying forever.
                        await self.bot.extreme.complete_action(action.id)
                    except Exception:
                        await self.bot.extreme.release_action(action.id)
                        log.exception('scheduled action failed id=%s; will retry',action.id)
            except asyncio.CancelledError: raise
            except Exception: log.exception('scheduler tick failed')
            await asyncio.sleep(self.interval)
    async def close(self):
        self.stop.set()
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
            self.task=None
