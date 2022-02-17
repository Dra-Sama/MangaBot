from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from img2pdf.core import fld2pdf
from manhuako import ManhuaKoClient, ManhuaCard, ManhuaChapter
import os

from pyrogram import Client
from typing import Dict


manhuas: Dict[str, ManhuaCard] = {}
chapters: Dict[str, ManhuaChapter] = {}
manhuako = ManhuaKoClient()
bot = Client('bot',
             api_id=int(os.getenv('API_ID')),
             api_hash=os.getenv('API_HASH'),
             bot_token=os.getenv('BOT_TOKEN'))


@bot.on_message()
async def on_message(client, message: Message):
    results = await manhuako.search(message.text)
    for result in results:
        manhuas[result.unique()] = result
    await bot.send_message(message.chat.id,
                           "This is the result of your search",
                           reply_markup=InlineKeyboardMarkup([
                               [InlineKeyboardButton(result.name, callback_data=result.unique())] for result in results
                           ]))


async def manhua_click(client, callback: CallbackQuery):
    manhua = manhuas[callback.data]
    results = await manhuako.get_chapters(manhua)
    
    for result in results:
        chapters[result.unique()] = result
    
    await bot.send_photo(callback.from_user.id, manhua.picture_url, f'{manhua.name}\n'
                                                                    f'{manhua.url}', reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton(result.name, result.unique())] for result in results
    ]))


async def chapter_click(client, callback):
    chapter = chapters[callback.data]
    pictures_folder = await manhuako.download_pictures(chapter)
    
    pdf = fld2pdf(pictures_folder, f'{chapter.manhua.name} - {chapter.name}')
    
    await bot.send_document(callback.from_user.id, pdf)


@bot.on_callback_query()
async def on_callback_query(client, callback: CallbackQuery):
    if callback.data in manhuas:
        await manhua_click(client, callback)
    elif callback.data in chapters:
        await chapter_click(client, callback)
    else:
        await bot.answer_callback_query(callback.id, 'This is an old button, please redo the search', show_alert=True)

