import asyncio, logging
import discord
log=logging.getLogger('bot.scheduler')
class Scheduler:
    def __init__(self,bot,interval=5): self.bot=bot; self.interval=interval; self.task=None; self.stop=asyncio.Event()
    async def start(self): self.task=asyncio.create_task(self.run())
    async def run(self):
        while not self.stop.is_set():
            try:
                for r in await self.bot.platform.due_reminders():
                    ch=self.bot.get_channel(r.channel_id)
                    if ch:
                        try: await ch.send(f'⏰ <@{r.user_id}> {r.message}')
                        except Exception: log.exception('reminder delivery failed')
                for action in await self.bot.extreme.due_actions():
                    guild=self.bot.get_guild(action.guild_id)
                    if not guild:
                        continue
                    try:
                        if action.action == 'timeout':
                            member = guild.get_member(action.target_id)
                            if not member:
                                continue
                            await member.timeout(None, reason='V16 temporary timeout expired')
                        elif action.action == 'ban':
                            # Banned users are commonly absent from the member cache.
                            await guild.unban(discord.Object(id=action.target_id), reason='V16 temporary ban expired')
                        else:
                            log.warning('unknown scheduled action id=%s action=%s', action.id, action.action)
                            continue
                        await self.bot.extreme.complete_action(action.id)
                    except discord.NotFound:
                        # The desired end state is already true (e.g. an already
                        # unbanned user). Mark the action complete rather than retrying forever.
                        await self.bot.extreme.complete_action(action.id)
                    except Exception:
                        log.exception('scheduled action failed id=%s; will retry',action.id)
            except asyncio.CancelledError: raise
            except Exception: log.exception('scheduler tick failed')
            await asyncio.sleep(self.interval)
    async def close(self):
        self.stop.set()
        if self.task: self.task.cancel()
