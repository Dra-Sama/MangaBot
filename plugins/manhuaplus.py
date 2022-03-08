from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote, quote_plus

from bs4 import BeautifulSoup

from plugins.client import MangaClient, MangaCard, MangaChapter


class ManhuaPlusClient(MangaClient):

    base_url = urlparse("https://manhuaplus.com/")
    search_url = base_url.geturl()
    search_param = 's'
    chapters = 'ajax/chapters/'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name="Manhuaplus", **kwargs):
        super().__init__(*args, name=name, headers=self.headers, **kwargs)

    def mangas_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")

        cards = bs.find("div", {"class": "c-tabs-item"})

        if not cards:
            return []

        mangas = cards.find_all('div', {'class': 'tab-thumb'})
        names = [manga.a.get('title') for manga in mangas]
        url = [manga.a.get('href') for manga in mangas]

        images = [manga.findNext('img').get('data-src') for manga in mangas]

        mangas = [MangaCard(self, *tup) for tup in zip(names, url, images)]

        return mangas

    def chapters_from_page(self, page: bytes, manga: MangaCard = None):
        bs = BeautifulSoup(page, "html.parser")

        lis = bs.find_all("li", {"class": "wp-manga-chapter"})

        items = [li.findNext('a') for li in lis]

        links = [item.get('href') for item in items]
        texts = [item.string.strip() for item in items]

        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))

    async def pictures_from_chapters(self, content: bytes, response=None):
        bs = BeautifulSoup(content, "html.parser")

        ul = bs.find("div", {"class": "reading-content"})

        images = ul.find_all('img')

        images_url = [quote(img.get('src'), safe=':/') for img in images]

        return images_url

    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        query = quote_plus(query)

        request_url = self.search_url

        if query:
            request_url += f'?{self.search_param}={query}&post_type=wp-manga'

        content = await self.get_url(request_url)

        return self.mangas_from_page(content)

    async def get_chapters(self, manga_card: MangaCard, page: int = 1) -> List[MangaChapter]:

        request_url = f'{manga_card.url}{self.chapters}'

        content = await self.get_url(request_url, method='post')

        return self.chapters_from_page(content, manga_card)[(page - 1) * 20:page * 20]

    async def iter_chapters(self, manga_url: str, manga_name) -> AsyncIterable[MangaChapter]:
        manga_card = MangaCard(self, manga_name, manga_url, '')

        request_url = f'{manga_card.url}{self.chapters}'

        content = await self.get_url(request_url, method='post')

        for chapter in self.chapters_from_page(content, manga_card):
            yield chapter

    async def contains_url(self, url: str):
        return url.startswith(self.base_url.geturl())
