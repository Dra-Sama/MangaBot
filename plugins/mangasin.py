from typing import List, AsyncIterable
import json
from urllib.parse import urlparse, urljoin, quote, quote_plus
from dataclasses import dataclass

from bs4 import BeautifulSoup
from bs4.element import PageElement

from plugins.client import MangaClient, MangaCard, MangaChapter
from models import LastChapter

@dataclass
class MangaSinMangaCard(MangaCard):
    data: str

class MangasInClient(MangaClient):

    base_url = urlparse("https://mangas.in/")
    search_url = urljoin(base_url.geturl(), "search")
    search_param = 'q'

    pre_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name="MangasIn", **kwargs):
        super().__init__(*args, name=name, headers=self.pre_headers, **kwargs)

    def build_cover_url(self, data: str):
        return f"{self.base_url.geturl()}uploads/manga/{data}/cover/cover_250x350.jpg"

    def build_manga_url(self, data: str):
        return f"{self.base_url.geturl()}manga/{data}"

    def build_chapter_url(self, manga: MangaSinMangaCard, chapter: str):
        return f"{self.base_url.geturl()}manga/{manga.data}/{chapter}"

    def build_chapter_name(self, li_tag: PageElement):
        name_div = li_tag.findNext('eee')
        if not name_div or name_div.findPrevious('li') != li_tag:
            name_div = li_tag.findNext('fff')
        name = name_div.a.text

        number = li_tag.findNext('a').get('data-number')

        return f"{number} - {name}"

    def mangas_from_page(self, page: bytes):
        mangas = json.loads(page)

        names = [manga['value'] for manga in mangas]
        datas = [manga['data'] for manga in mangas]
        url = [self.build_manga_url(data) for data in datas]
        images = [self.build_cover_url(data) for data in datas]

        mangas = [MangaSinMangaCard(self, *tup) for tup in zip(names, url, images, datas)]

        return mangas

    def chapters_from_page(self, page: bytes, manga: MangaCard = None):
        bs = BeautifulSoup(page, "html.parser")

        lis: List[PageElement] = bs.findAll("li", recursive=True)
        lis: List[PageElement] = [li for li in lis if isinstance(li.get('class'), list) and len(li.get('class')) > 0 and li.get('class')[0].startswith('volume-')]

        items = [li for li in lis]

        texts = [self.build_chapter_name(item) for item in items]
        links = [item.findNext('daka').a.get('href') for item in items]

        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))

    def updates_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")

        manga_items: List[PageElement] = bs.find_all("div", {"class": "manga-item"})

        urls = dict()

        for manga_item in manga_items:

            manga_url = manga_item.findNext('a').findNextSibling('a').get('href')

            chapter_item = manga_item.findNext("div", {"class": "manga-chapter"})
            chapter_url = chapter_item.findNext("a").get('href')

            urls[manga_url] = chapter_url

        return urls

    async def pictures_from_chapters(self, content: bytes, response=None):
        bs = BeautifulSoup(content, "html.parser")

        ul = bs.find("div", {"id": "all"})

        images = ul.find_all('img')

        images_url = [quote(img.get('data-src'), safe=':/%') for img in images]

        return images_url


    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        query = quote_plus(query)

        request_url = f'{self.search_url}'

        if query:
            request_url += f'?{self.search_param}={query}'

        content = await self.get_url(request_url)

        return self.mangas_from_page(content)[(page - 1) * 10:page * 10]

    async def get_chapters(self, manga_card: MangaCard, page: int = 1) -> List[MangaChapter]:

        request_url = f'{manga_card.url}'

        content = await self.get_url(request_url)

        return self.chapters_from_page(content, manga_card)[(page - 1) * 10:page * 10]

    async def iter_chapters(self, manga_url: str, manga_name) -> AsyncIterable[MangaChapter]:
        manga = MangaCard(self, manga_name, manga_url, '')

        request_url = f'{manga.url}'

        content = await self.get_url(request_url)

        for chapter in self.chapters_from_page(content, manga):
            yield chapter

    async def contains_url(self, url: str):
        return url.startswith(self.base_url.geturl())

    async def check_updated_urls(self, last_chapters: List[LastChapter]):

        content = await self.get_url(self.base_url.geturl())

        updates = self.updates_from_page(content)

        updated = [lc.url for lc in last_chapters if updates.get(lc.url) and updates.get(lc.url) != lc.chapter_url]
        not_updated = [lc.url for lc in last_chapters if not updates.get(lc.url) or updates.get(lc.url) == lc.chapter_url]

        return updated, not_updated
