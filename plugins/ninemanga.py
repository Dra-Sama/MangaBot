from typing import List, AsyncIterable, Optional
from urllib.parse import urlparse, urljoin, quote, quote_plus

import aiohttp.http
from aiohttp import ClientResponse
from bs4 import BeautifulSoup

from plugins.client import MangaClient, MangaCard, MangaChapter, LastChapter


class NineMangaClient(MangaClient):

    base_url = urlparse("https://www.ninemanga.com/")
    search_param = 'wd'
    query_param = 'waring=1'

    pre_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    def __init__(self, *args, name="NineManga", language=None, **kwargs):
        if language is None:
            language = 'en'
        else:
            self.base_url = urlparse(f"https://{language}.ninemanga.com/")
        self.search_url = urljoin(self.base_url.geturl(), 'search/')
        self.updates_url = self.base_url.geturl()
        super().__init__(*args, name=name, headers=self.pre_headers, **kwargs)

    def mangas_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")

        container = bs.find("ul", {"class": "direlist"})

        cards = container.find_all("li")

        mangas = [card.findNext('a', {'class': 'bookname'}) for card in cards]
        names = [manga.string.strip().title() for manga in mangas]
        url = [manga.get("href") for manga in mangas]
        images = [card.findNext("img").get("src") for card in cards]

        mangas = [MangaCard(self, *tup) for tup in zip(names, url, images)]

        return mangas

    def chapters_from_page(self, page: bytes, manga: MangaCard = None):
        bs = BeautifulSoup(page, "html.parser")

        container = bs.find("div", {"class": "chapterbox"})

        lis = container.find_all("li")

        items = [li.findNext('a') for li in lis]

        links = [item.get("href") for item in items]
        texts = [item.get("title").strip() for item in items]

        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))

    def updates_from_page(self, content):
        bs = BeautifulSoup(content, "html.parser")

        container = bs.find("ul", {"class": "homeupdate"})

        manga_items = container.find_all("li")

        urls = dict()

        for manga_item in manga_items[:20]:
            manga_url = manga_item.findNext("a").get("href")

            if manga_url in urls:
                continue

            chapter_url = manga_item.findNext("dl").findNext("a").get("href")

            urls[manga_url] = chapter_url

        return urls

    async def pictures_from_chapters(self, content: bytes, response: Optional[ClientResponse] = None):
        bs = BeautifulSoup(content, "html.parser")

        container = bs.find("select", {"id": "page"})

        options = container.find_all("option")

        count = 10
        total = len(options)
        pages = (total - 1) // count

        images_url = []
        for page in range(pages):
            url = f'{str(response.url)[:-5]}-{count}-{(page + 1)}.html'
            content = await self.get_url(url)
            bs = BeautifulSoup(content, "html.parser")
            images_url += [img.get("src") for img in bs.find_all("img", {"class": "manga_pic"})]

        return images_url

    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        query = quote_plus(query)

        request_url = self.search_url

        if query:
            request_url += f'?{self.search_param}={query}'

        content = await self.get_url(request_url)

        return self.mangas_from_page(content)

    async def get_chapters(self, manga_card: MangaCard, page: int = 1) -> List[MangaChapter]:

        request_url = f'{manga_card.url}?{self.query_param}'

        content = await self.get_url(request_url)

        return self.chapters_from_page(content, manga_card)[(page - 1) * 20:page * 20]

    async def iter_chapters(self, manga_url: str, manga_name) -> AsyncIterable[MangaChapter]:
        manga_card = MangaCard(self, manga_name, manga_url, '')

        request_url = f'{manga_card.url}?{self.query_param}'

        content = await self.get_url(request_url)

        for chapter in self.chapters_from_page(content, manga_card):
            yield chapter

    async def contains_url(self, url: str):
        return url.startswith(self.base_url.geturl())

    @staticmethod
    def get_chapter_number_from_url(url):
        if url.endswith('/'):
            url = url[:-1]
        if url.endswith('.html'):
            url = url[:-5]
        return url.split('/')[-1]

    async def check_updated_urls(self, last_chapters: List[LastChapter]):

        content = await self.get_url(self.updates_url)

        updates = self.updates_from_page(content)

        updated = [lc.url for lc in last_chapters if updates.get(lc.url) and
                   self.get_chapter_number_from_url(updates.get(lc.url)) != self.get_chapter_number_from_url(lc.chapter_url)]
        not_updated = [lc.url for lc in last_chapters if not updates.get(lc.url) or
                       self.get_chapter_number_from_url(updates.get(lc.url)) == self.get_chapter_number_from_url(lc.chapter_url)]

        return updated, not_updated
