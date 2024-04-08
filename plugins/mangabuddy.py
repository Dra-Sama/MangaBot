import re
from dataclasses import dataclass
from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote, quote_plus

from bs4 import BeautifulSoup

from models import LastChapter
from plugins.client import MangaClient, MangaCard, MangaChapter


@dataclass
class MangaBuddyCard(MangaCard):
    read_url: str

    def get_url(self):
        return self.read_url


class MangaBuddyClient(MangaClient):
    base_url = urlparse("https://mangabuddy.com/")
    search_url = urljoin(base_url.geturl(), "search")
    search_param = 'q'
    home_page = urljoin(base_url.geturl(), "home-page")
    img_server = "https://s1.mbbcdnv1.xyz/file/img-mbuddy/manga/"

    pre_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name="MangaBuddy", **kwargs):
        super().__init__(*args, name=name, headers=self.pre_headers, **kwargs)

    def mangas_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")

        cards = bs.find_all("div", {"class": "book-item"})

        mangas = [card.a for card in cards if card.a is not None]
        names = [manga.get("title").strip() for manga in mangas]
        read_url = [urljoin(self.base_url.geturl(), manga.get('href').strip()) for manga in mangas]
        url = [f'https://mangabuddy.com/api/manga{manga.get("href").strip()}/chapters?source=detail' for manga in mangas]
        images = [manga.find("img").get('data-src').strip() for manga in mangas]

        mangas = [MangaBuddyCard(self, *tup) for tup in zip(names, url, images, read_url)]

        return mangas

    def chapters_from_page(self, page: bytes, manga: MangaCard = None):
        bs = BeautifulSoup(page, "html.parser")

        ul = bs.find('ul', {'id': 'chapter-list'})

        lis = ul.findAll('li')
        a_elems = [li.find('a') for li in lis]

        links = [urljoin(self.base_url.geturl(), a.get('href')) for a in a_elems]
        texts = [a.findNext('strong', {'class': 'chapter-title'}).text.strip() for a in a_elems]

        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))

    def updates_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")

        div = bs.find('div', {'class': 'container__left'})

        manga_items = div.findAll('div', {'class': 'book-item'})

        urls = dict()

        for manga_item in manga_items:

            manga_url_part = manga_item.findNext('a').get('href')
            manga_url = f'https://mangabuddy.com/api/manga{manga_url_part}/chapters?source=detail'

            chapter_item = manga_item.findNext("div", {"class": "chap-item"})
            if not chapter_item or not chapter_item.a:
                continue
            chapter_url = urljoin(self.base_url.geturl(), chapter_item.a.get('href'))

            if manga_url not in urls:
                urls[manga_url] = chapter_url

        return urls

    async def pictures_from_chapters(self, content: bytes, response=None):

        regex = rb"var chapImages = '(.*)'"

        imgs = re.findall(regex, content)[0].decode().split(',')

        images_url = [img for img in imgs]

        return images_url

    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        request_url = self.search_url

        if query:
            request_url = f'{request_url}?{self.search_param}={quote_plus(query)}'

        content = await self.get_url(request_url)

        return self.mangas_from_page(content)[(page - 1) * 20:page * 20]

    async def get_chapters(self, manga_card: MangaCard, page: int = 1) -> List[MangaChapter]:

        request_url = f'{manga_card.url}'

        content = await self.get_url(request_url)

        return self.chapters_from_page(content, manga_card)[(page - 1) * 20:page * 20]

    async def iter_chapters(self, manga_url: str, manga_name) -> AsyncIterable[MangaChapter]:
        manga_card = MangaCard(self, manga_name, manga_url, '')

        request_url = f'{manga_card.url}'

        content = await self.get_url(request_url)

        for chapter in self.chapters_from_page(content, manga_card):
            yield chapter

    async def contains_url(self, url: str):
        return url.startswith(self.base_url.geturl())

    async def check_updated_urls(self, last_chapters: List[LastChapter]):

        content = await self.get_url(self.home_page)

        updates = self.updates_from_page(content)

        updated = [lc.url for lc in last_chapters if updates.get(lc.url) and updates.get(lc.url) != lc.chapter_url]
        not_updated = [lc.url for lc in last_chapters if not updates.get(lc.url)
                       or updates.get(lc.url) == lc.chapter_url]

        return updated, not_updated

    async def get_cover(self, manga_card: MangaCard, *args, **kwargs):
        headers = {**self.pre_headers, 'Referer': self.base_url.geturl()}
        return await super(MangaBuddyClient, self).get_cover(manga_card, *args, headers=headers, **kwargs)

    async def get_picture(self, manga_chapter: MangaChapter, url, *args, **kwargs):
        headers = {**self.pre_headers, 'Referer': self.base_url.geturl()}
        return await super(MangaBuddyClient, self).get_picture(manga_chapter, url, *args, headers=headers, **kwargs)
