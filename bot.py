import re

from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from img2pdf.core import fld2pdf
from manhuako import ManhuaKoClient, ManhuaCard, ManhuaChapter
import os

from pyrogram import Client
from typing import Dict

from pagination import Pagination

manhuas: Dict[str, ManhuaCard] = {}
chapters: Dict[str, ManhuaChapter] = {}
pdfs: Dict[str, str] = {}
paginations: Dict[int, Pagination] = {}
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


async def manhua_click(client, callback: CallbackQuery, pagination: Pagination = None):
    if pagination is None:
        pagination = Pagination()
        paginations[pagination.id] = pagination

    if pagination.manhua is None:
        manhua = manhuas[callback.data]
        pagination.manhua = manhua
        
    results = await manhuako.get_chapters(pagination.manhua, pagination.page)
    
    for result in results:
        chapters[result.unique()] = result
    
    prev = [InlineKeyboardButton('<<', f'{pagination.id}_{pagination.page - 1}')]
    next_ = [InlineKeyboardButton('>>', f'{pagination.id}_{pagination.page + 1}')]
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(result.name, result.unique())] for result in results
    ] + ([prev] if pagination.page > 1 else [prev, next_]))
    
    if pagination.message is None:
        message = await bot.send_photo(callback.from_user.id,
                                       pagination.manhua.picture_url,
                                       f'{pagination.manhua.name}\n'
                                       f'{pagination.manhua.url}', reply_markup=buttons)
        pagination.message = message
    else:
        await bot.edit_message_reply_markup(
            callback.from_user.id,
            pagination.message.message_id,
            reply_markup=buttons
        )


async def chapter_click(client, callback):
    chapter = chapters[callback.data]
    pictures_folder = await manhuako.download_pictures(chapter)
    
    if chapter.url not in pdfs:
        pdf = fld2pdf(pictures_folder, f'{chapter.manhua.name} - {chapter.name}')
        message = await bot.send_document(callback.from_user.id, pdf)
        pdfs[chapter.url] = message.document.file_id
    else:
        message = await bot.send_document(callback.from_user.id, pdfs[chapter.url])


async def pagination_click(client: Client, callback: CallbackQuery):
    pagination_id, page = map(int, callback.data.split('_'))
    pagination = paginations[pagination_id]
    pagination.page = page
    await manhua_click(client, callback, pagination)
    

def is_pagination_data(data: str):
    return re.match(r'\d+_\d+', data) and int(data.split('_')[0]) in paginations


@bot.on_callback_query()
async def on_callback_query(client, callback: CallbackQuery):
    if callback.data in manhuas:
        await manhua_click(client, callback)
    elif callback.data in chapters:
        await chapter_click(client, callback)
    elif is_pagination_data(callback.data):
        await pagination_click(client, callback)
    else:
        await bot.answer_callback_query(callback.id, 'This is an old button, please redo the search', show_alert=True)

