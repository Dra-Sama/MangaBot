import asyncio as aio
import os

from logger import logger
from bot import bot, manga_updater, chapter_creation
from models import DB
from config import env_vars


PIC = "https://te.legra.ph/file/5a2a761e6a899163db6d4.jpg"
C_Group=env_vars.get('C_GROUP')

async def async_main():
    db = DB()
    await db.connect()
    
if __name__ == '__main__':
    loop = aio.get_event_loop_policy().get_event_loop()
    loop.run_until_complete(async_main())
    loop.create_task(manga_updater())
    bot.start()
    bot.send_photo({C_Group}, photo=PIC, caption="Hey Guys!. I am Alive")
    idle()
    bot.stop()
