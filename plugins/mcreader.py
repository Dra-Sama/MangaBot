from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote, quote_plus
import json
import re

from bs4 import BeautifulSoup
from bs4.element import PageElement

from plugins.client import MangaClient, MangaCard, MangaChapter, LastChapter


class McReaderClient(MangaClient):

    base_url = urlparse("https://www.mcreader.net/")
    search_url = urljoin(base_url.geturl(), 'autocomplete')
    search_param = 'term'
    manga_url = urljoin(base_url.geturl(), 'manga')
    chapters = 'all-chapters/'
    latest_uploads = urljoin(base_url.geturl(), 'jumbo/manga/')
    manga_cover = 'https://images.novel-fast.club/avatar/288x412'

    pre_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name="McReader", **kwargs):
        super().__init__(*args, name=name, headers=self.pre_headers, **kwargs)

    def mangas_from_page(self, page: bytes):
        mangas = json.loads(page)

        names = [manga['manga_name'] for manga in mangas]
        url = [f'{self.manga_url}/{manga["manga_slug"]}/' for manga in mangas]

        images = [f'{self.manga_cover}/{manga["manga_cover"]}' for manga in mangas]

        mangas = [MangaCard(self, *tup) for tup in zip(names, url, images)]

        return mangas

    def chapters_from_page(self, page: bytes, manga: MangaCard = None):
        bs = BeautifulSoup(page, "html.parser")

        ul = bs.find('ul', {'class': 'chapter-list'})

        lis = ul.find_all('li')

        items = [li.findNext('a') for li in lis]

        links = [urljoin(self.base_url.geturl(), item.get('href')) for item in items]
        texts = [item.findNext('strong', {'class': 'chapter-title'}).string.strip().split('-eng')[0].replace('-', '.') for item in items]

        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))

    def updates_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")

        ul = bs.find('ul', {'class': 'novel-list'})

        manga_items: List[PageElement] = ul.find_all("li")

        urls = dict()

        for manga_item in manga_items:

            manga_url = urljoin(self.base_url.geturl(), manga_item.findNext('a').get('href'))

            if manga_url in urls:
                continue

            chapter_item = manga_item.findNext("h5", {"class": "chapter-title"})
            chapter_text: str = chapter_item.text.strip()
            m = re.match(r'.* (.*)-eng.*', chapter_text)
            number = m.group(1)
            number.replace('-', '.')

            urls[manga_url] = number

        return urls

    async def pictures_from_chapters(self, content: bytes, response=None):
        bs = BeautifulSoup(content, "html.parser")

        ul = bs.find("div", {"id": "chapter-reader"})

        images = ul.find_all('img')

        images_url = [quote(img.get('src'), safe=':/%') for img in images]

        return images_url

    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        query = quote(query)

        request_url = self.search_url

        if query:
            request_url += f'?{self.search_param}={query}'

        content = await self.get_url(request_url)

        return self.mangas_from_page(content)[(page - 1) * 15:page * 15]

    async def get_chapters(self, manga_card: MangaCard, page: int = 1) -> List[MangaChapter]:

        request_url = f'{manga_card.url}/{self.chapters}'

        content = await self.get_url(request_url)

        return self.chapters_from_page(content, manga_card)[(page - 1) * 20:page * 20]

    async def iter_chapters(self, manga_url: str, manga_name) -> AsyncIterable[MangaChapter]:
        manga_card = MangaCard(self, manga_name, manga_url, '')

        request_url = f'{manga_card.url}/{self.chapters}'

        content = await self.get_url(request_url)

        for chapter in self.chapters_from_page(content, manga_card):
            yield chapter

    async def contains_url(self, url: str):
        return url.startswith(self.base_url.geturl())

    def number_from_url(self, url: str):
        return url.split('chapter-')[1].split('-eng')[0].replace('-', '.')

    async def check_updated_urls(self, last_chapters: List[LastChapter]):

        content = await self.get_url(self.latest_uploads)

        updates = self.updates_from_page(content)

        updated = [lc.url for lc in last_chapters if updates.get(lc.url) and updates.get(lc.url) != self.number_from_url(lc.chapter_url)]
        not_updated = [lc.url for lc in last_chapters if not updates.get(lc.url) or updates.get(lc.url) == self.number_from_url(lc.chapter_url)]

        return updated, not_updated