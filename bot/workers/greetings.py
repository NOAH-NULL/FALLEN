import asyncio
import time
import discord
from bot.core.metrics import WORK_QUEUE

class GreetingWorker:
    def __init__(self,bot,size=256,workers=4,max_event_age=30.0):
        self.bot=bot; self.queue=asyncio.Queue(maxsize=size); self.workers=workers; self.max_event_age=max(1.0,max_event_age); self.tasks=[]
    async def start(self):
        self.tasks=[asyncio.create_task(self._run(),name=f'greeting-worker-{i}') for i in range(self.workers)]
    async def submit(self,member,kind,force_channel=None,invite_id=None,invite_uses=0):
        try:
            self.queue.put_nowait((time.monotonic(),member,kind,force_channel,invite_id,invite_uses)); WORK_QUEUE.labels('greetings').set(self.queue.qsize()); return True
        except asyncio.QueueFull:
            WORK_QUEUE.labels('greetings').set(self.queue.qsize()); return False

    @staticmethod
    def _format(value, member, count, inviter_id=None, invite_uses=0):
        return (value or '').format(
            mention=member.mention, name=member.display_name, username=member.name,
            server=member.guild.name, count=count, membercount=count, inviter=(f'<@{inviter_id}>' if inviter_id else 'Unknown'), invites=invite_uses,
        )

    async def _run(self):
        while True:
            enqueued,member,kind,force,invite_id,invite_uses=await self.queue.get()
            try:
                age=time.monotonic()-enqueued
                if age > self.max_event_age:
                    self.bot.log.warning('dropping stale greeting age=%.2fs guild=%s kind=%s',age,member.guild.id,kind)
                    continue
                cfg=await self.bot.guild_config.get(member.guild.id)
                channel=force or member.guild.get_channel(cfg.get(f'{kind}_channel_id'))
                if channel:
                    background = cfg.get(f'{kind}_background_data') or cfg.get(f'{kind}_background')
                    buf=await self.bot.greetings.render(
                        member,kind,background,cfg.get(f'{kind}_message'),
                        member.guild.member_count or 0, inviter_id=invite_id, invite_uses=invite_uses
                    )
                    filename=f'{kind}.{self.bot.greetings.output_extension(buf)}'; embed=None
                    if cfg.get(f'{kind}_embed_enabled', True):
                        count=member.guild.member_count or 0
                        title=self._format(cfg.get(f'{kind}_embed_title'),member,count,invite_id,invite_uses)[:256]
                        description=self._format(cfg.get(f'{kind}_embed_description'),member,count,invite_id,invite_uses)[:4096]
                        embed=discord.Embed(title=title or None,description=description or None,color=int(cfg.get(f'{kind}_embed_color') or 5793266))
                        embed.set_image(url=f'attachment://{filename}')
                        embed.set_footer(text=f'{member.guild.name} • Member #{count}')
                    await channel.send(content=None,embed=embed,file=discord.File(buf,filename=filename))
            except asyncio.CancelledError: raise
            except Exception: self.bot.log.exception('greeting worker failed')
            finally:
                self.queue.task_done(); WORK_QUEUE.labels('greetings').set(self.queue.qsize())
    async def close(self):
        for t in self.tasks:t.cancel()
        if self.tasks:await asyncio.gather(*self.tasks,return_exceptions=True)
