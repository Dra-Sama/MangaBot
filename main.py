import asyncio as aio
import os

from logger import logger
from bot import bot, manga_updater, chapter_creation
from models import DB


PIC = "https://te.legra.ph/file/5a2a761e6a899163db6d4.jpg"

async def async_main():
    db = DB()
    await db.connect()
    
if __name__ == '__main__':
    loop = aio.get_event_loop_policy().get_event_loop()
    loop.run_until_complete(async_main())
    loop.create_task(manga_updater())
    bot.start()
    bot.send_photo(-1001723894782, photo=PIC, caption="Hey Guys! \n \nI'm alive.\n \nUse Me @Manga_Downloaderx_bot")
    idle()
    bot.stop()
