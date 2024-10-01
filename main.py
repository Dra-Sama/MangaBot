import asyncio as aio
from bot import *


async def async_main():
    db = DB()
    await db.connect()
    
if __name__ == '__main__':
    loop = aio.get_event_loop_policy().get_event_loop()
    loop.run_until_complete(async_main())
    loop.create_task(manga_updater())
    for i in range(10):
        loop.create_task(chapter_creation(i + 1))
    bot.run()
