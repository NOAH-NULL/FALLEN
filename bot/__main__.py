import asyncio
from bot.core.bot import Bot
from bot.core.config import Settings
from bot.core.logging import configure_logging
async def main():
    s=Settings(); configure_logging(s.log_level)
    async with Bot(s) as bot: await bot.start(s.token)
if __name__=='__main__': asyncio.run(main())
