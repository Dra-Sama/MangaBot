from pathlib import Path
from typing import List
from urllib.parse import urlparse, urljoin, quote, quote_plus

from bs4 import BeautifulSoup

from plugins.client import MangaClient, MangaCard, MangaChapter


class ManhuaKoClient(MangaClient):

    base_url = urlparse("https://manhuako.com/")
    search_url = urljoin(base_url.geturl(), "home/search/")
    search_param = 'mq'

    def __init__(self, *args, name="Manhuako", **kwargs):
        super().__init__(*args, name=name, **kwargs)

    def mangas_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")

        cards = bs.find_all("div", {"class": "card"})

        manhuas = [card.findNext('a', {'class': 'white-text'}) for card in cards]
        names = [manhua.string for manhua in manhuas]
        url = [manhua.get('href') for manhua in manhuas]

        images = [card.findNext('img').get('src') for card in cards]

        manhuas = [MangaCard(self, *tup) for tup in zip(names, url, images)]

        return manhuas

    def chapters_from_page(self, page: bytes, manhua: MangaCard = None):
        bs = BeautifulSoup(page, "html.parser")

        lis = bs.find_all("li", {"class": "collection-item"})

        items = [li.findNext('a') for li in lis]

        links = [item.get('href') for item in items]
        texts = [item.string for item in items]

        return list(map(lambda x: MangaChapter(self, x[0], x[1], manhua, []), zip(texts, links)))

    @staticmethod
    def pictures_from_chapters(content: bytes):
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

        file_name = f'search_{query}_page_{page}.html'

        content = await self.get_url(file_name, request_url)

        return self.mangas_from_page(content)

    async def get_chapters(self, manhua_card: MangaCard, page: int = 1) -> List[MangaChapter]:

        request_url = f'{manhua_card.url}/page/{page}'
        file_name = f'chapters_{manhua_card.name}_page_{page}.html'

        content = await self.get_url(file_name, request_url)

        return self.chapters_from_page(content, manhua_card)
