import asyncio
import aiofiles
import aiohttp
import telethon
from telethon.events import NewMessage, MessageEdited
from telethon.tl.custom import Message
import os
from functools import partial

if __name__ == '__main__':
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    bot_token = os.getenv('BOT_TOKEN')
    if not api_id or not api_hash or not bot_token:
        print("Proper env variables need to be set")
    try:
        api_id = int(api_id)
    except:
        print("API_ID must be of type int")
        exit(0)
    bot = telethon.TelegramClient('bot', api_id=api_id, api_hash=api_hash).start(bot_token=bot_token)
    
    async def progress_handler(message: Message, received_bytes, total_bytes):
        await message.edit(f'Downloading {round(received_bytes * 100 / total_bytes, 2)}')
    
    async def todus_upload(message: Message, filepath):
        message = await message.edit('Uploading')
        message = await message.edit('Uploaded')
    
    @bot.on(NewMessage(pattern='/start'))
    async def start(event: Message):
        await event.respond('Send me a file and i will upload it to s3 todus server.')
        
    @bot.on(NewMessage())
    async def upload(event: Message):
        if not event.is_private or not event.file:
            return
        message: Message = await event.respond('Adding request to queue')
        message = await message.edit('Downloading')
        filename = await message.file.name
        filepath = f'./{filename}'
        file = await message.download_media(file=filepath, progress_callback=partial(progress_handler, (event,)))
        message = await message.edit('Downloaded')
        await todus_upload(message, filepath)
