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
                    guild=self.bot.get_guild(action.guild_id); member=guild.get_member(action.target_id) if guild else None
                    if not member: continue
                    try:
                        if action.action == 'timeout': await member.timeout(None, reason='V16 temporary timeout expired')
                        elif action.action == 'ban': await guild.unban(discord.Object(id=action.target_id), reason='V16 temporary ban expired')
                    except Exception: log.exception('scheduled action failed id=%s',action.id)
            except asyncio.CancelledError: raise
            except Exception: log.exception('scheduler tick failed')
            await asyncio.sleep(self.interval)
    async def close(self):
        self.stop.set()
        if self.task: self.task.cancel()
