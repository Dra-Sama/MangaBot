import asyncio as aio
import os

from logger import logger
from bot import bot, manga_updater, chapter_creation
from models import DB


PIC = "https://graph.org//file/925c5eee60879804be1d9.jpg"
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
