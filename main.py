from pyrogram import Client, filters

from manhuako import ManhuaKoClient

import asyncio as aio
from bot import bot
from models import DB

loop = aio.new_event_loop()
db = DB()
loop.run_until_complete(db.connect())
bot.run()

