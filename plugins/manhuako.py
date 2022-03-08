from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote, quote_plus

from bs4 import BeautifulSoup

from plugins.client import MangaClient, MangaCard, MangaChapter


class ManhuaKoClient(MangaClient):

    base_url = urlparse("https://manhuako.com/")
    search_url = urljoin(base_url.geturl(), "home/search")
    search_param = 'mq'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name="Manhuako", **kwargs):
        super().__init__(*args, name=name, headers=self.headers, **kwargs)

    def mangas_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")

        cards = bs.find_all("div", {"class": "card"})

        mangas = [card.findNext('a', {'class': 'white-text'}) for card in cards]
        names = [manga.string for manga in mangas]
        url = [manga.get('href') for manga in mangas]

        images = [card.findNext('img').get('src') for card in cards]

        mangas = [MangaCard(self, *tup) for tup in zip(names, url, images)]

        return mangas

    def chapters_from_page(self, page: bytes, manga: MangaCard = None):
        bs = BeautifulSoup(page, "html.parser")

        lis = bs.find_all("li", {"class": "collection-item"})

        items = [li.findNext('a') for li in lis]

        links = [item.get('href') for item in items]
        texts = [item.string for item in items]

        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))

    async def pictures_from_chapters(self, content: bytes):
        bs = BeautifulSoup(content, "html.parser")

        ul = bs.find("div", {"id": "pantallaCompleta"})

        images = ul.find_all('img')

        images_url = [quote(img.get('src'), safe=':/') for img in images]

        return images_url

    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        query = quote_plus(query)

        request_url = f'{self.search_url}/page/{page}'

        if query:
            request_url += f'?{self.search_param}={query}'

        content = await self.get_url(request_url)

        return self.mangas_from_page(content)

    async def get_chapters(self, manga_card: MangaCard, page: int = 1) -> List[MangaChapter]:

        request_url = f'{manga_card.url}/page/{page}'

        content = await self.get_url(request_url)

        return self.chapters_from_page(content, manga_card)

    async def iter_chapters(self, manga_url: str, manga_name) -> AsyncIterable[MangaChapter]:
        manga = MangaCard(self, manga_name, manga_url, '')
        page = 1
        while page > 0:
            chapters = await self.get_chapters(manga_card=manga, page=page)
            if not chapters:
                break
            for chapter in chapters:
                yield chapter

    async def contains_url(self, url: str):
        return url.startswith(self.base_url.geturl())
