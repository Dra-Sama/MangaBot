from pathlib import Path
from typing import List
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

    @staticmethod
    def pictures_from_chapters(content: bytes):
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

        file_name = f'search_{query}_page_{page}.html'

        content = await self.get_url(file_name, request_url)

        return self.mangas_from_page(content)

    async def get_chapters(self, manga_card: MangaCard, page: int = 1) -> List[MangaChapter]:

        request_url = f'{manga_card.url}{self.chapters}'
        file_name = f'chapters_{manga_card.name}_page_{page}.html'

        content = await self.get_url(file_name, request_url, method='post')

        return self.chapters_from_page(content, manga_card)[(page - 1) * 20:page * 20]
