import re

from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from img2pdf.core import fld2pdf
from plugins import MangaClient, ManhuaKoClient, MangaCard, MangaChapter, ManhuaPlusClient
import os

from pyrogram import Client
from typing import Dict, Tuple

from models.db import DB, ChapterFile
from pagination import Pagination

mangas: Dict[str, MangaCard] = {}
chapters: Dict[str, MangaChapter] = {}
pdfs: Dict[str, str] = {}
paginations: Dict[int, Pagination] = {}
queries: Dict[str, Tuple[MangaClient, str]] = {}

plugins: Dict[str, MangaClient] = {
    "ManhuaKo": ManhuaKoClient(),
    "Manhuaplus": ManhuaPlusClient()
}


def split_list(li):
    return [li[x: x+2] for x in range(0, len(li), 2)]


bot = Client('bot',
             api_id=int(os.getenv('API_ID')),
             api_hash=os.getenv('API_HASH'),
             bot_token=os.getenv('BOT_TOKEN'))


@bot.on_message()
async def on_message(client, message: Message):
    for identifier, manga_client in plugins.items():
        queries[f"query_{identifier}_{hash(message.text)}"] = (manga_client, message.text)
    await bot.send_message(message.chat.id, "Select search plugin", reply_markup=InlineKeyboardMarkup(
        split_list([InlineKeyboardButton(identifier, callback_data=f"query_{identifier}_{hash(message.text)}")
         for identifier, manga_client in plugins.items()])
    ))


async def plugin_click(client, callback: CallbackQuery):
    manga_client, query = queries[callback.data]
    results = await manga_client.search(query)
    if not results:
        await bot.send_message(callback.from_user.id, "No manga found for given query.")
        return
    for result in results:
        mangas[result.unique()] = result
    await bot.send_message(callback.from_user.id,
                           "This is the result of your search",
                           reply_markup=InlineKeyboardMarkup([
                               [InlineKeyboardButton(result.name, callback_data=result.unique())] for result in results
                           ]))


async def manga_click(client, callback: CallbackQuery, pagination: Pagination = None):
    if pagination is None:
        pagination = Pagination()
        paginations[pagination.id] = pagination

    if pagination.manga is None:
        manga = mangas[callback.data]
        pagination.manga = manga
        
    results = await pagination.manga.client.get_chapters(pagination.manga, pagination.page)

    if not results:
        await callback.answer("Ups, no chapters there.", show_alert=True)
        return
    
    for result in results:
        chapters[result.unique()] = result
    
    prev = [InlineKeyboardButton('<<', f'{pagination.id}_{pagination.page - 1}')]
    next_ = [InlineKeyboardButton('>>', f'{pagination.id}_{pagination.page + 1}')]
    footer = [prev + next_] if pagination.page > 1 else [next_]
    
    buttons = InlineKeyboardMarkup(footer + [
        [InlineKeyboardButton(result.name, result.unique())] for result in results
    ] + footer)
    
    if pagination.message is None:
        message = await bot.send_photo(callback.from_user.id,
                                       pagination.manga.picture_url,
                                       f'{pagination.manga.name}\n'
                                       f'{pagination.manga.url}', reply_markup=buttons)
        pagination.message = message
    else:
        await bot.edit_message_reply_markup(
            callback.from_user.id,
            pagination.message.message_id,
            reply_markup=buttons
        )


async def chapter_click(client, callback):
    chapter = chapters[callback.data]
    db = DB()
    
    chapterFile: ChapterFile = await db.get(ChapterFile, chapter.url)
    
    if not chapterFile:
        pictures_folder = await chapter.client.download_pictures(chapter)
        pdf = fld2pdf(pictures_folder, f'{chapter.manga.name} - {chapter.name}')
        message = await bot.send_document(callback.from_user.id, pdf)
        await db.add(ChapterFile(url=chapter.url, file_id=message.document.file_id))
    else:
        message = await bot.send_document(callback.from_user.id, chapterFile.file_id)


async def pagination_click(client: Client, callback: CallbackQuery):
    pagination_id, page = map(int, callback.data.split('_'))
    pagination = paginations[pagination_id]
    pagination.page = page
    await manga_click(client, callback, pagination)
    

def is_pagination_data(callback: CallbackQuery):
    data = callback.data
    match = re.match(r'\d+_\d+', data)
    if not match:
        return False
    pagination_id = int(data.split('_')[0])
    if pagination_id not in paginations:
        return False
    pagination = paginations[pagination_id]
    if pagination.message.chat.id != callback.from_user.id:
        return False
    if pagination.message.message_id != callback.message.message_id:
        return False
    return True


@bot.on_callback_query()
async def on_callback_query(client, callback: CallbackQuery):
    if callback.data in queries:
        await plugin_click(client, callback)
    elif callback.data in mangas:
        await manga_click(client, callback)
    elif callback.data in chapters:
        await chapter_click(client, callback)
    elif is_pagination_data(callback):
        await pagination_click(client, callback)
    else:
        await bot.answer_callback_query(callback.id, 'This is an old button, please redo the search', show_alert=True)
        return
    await callback.answer()

