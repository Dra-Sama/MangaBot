from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote, quote_plus

from bs4 import BeautifulSoup
from bs4.element import PageElement

from plugins.client import MangaClient, MangaCard, MangaChapter, LastChapter


class ManhuaKoClient(MangaClient):

    base_url = urlparse("https://manhuako.com/")
    search_url = urljoin(base_url.geturl(), "home/search")
    search_param = 'mq'

    pre_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name="Manhuako", **kwargs):
        super().__init__(*args, name=name, headers=self.pre_headers, **kwargs)

    def mangas_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")

        cards = bs.find_all("div", {"class": "card"})

        cards = [card for card in cards if card.findNext('p', {'class': 'type'}).text != "Novela"]

        mangas = [card.findNext('a', {'class': 'white-text'}) for card in cards]
        names = [manga.string for manga in mangas]
        url = [manga.get('href') for manga in mangas]

        images = [card.findNext('img').get('src') for card in cards]

        mangas = [MangaCard(self, *tup) for tup in zip(names, url, images)]

        return mangas

    def chapters_from_page(self, page: bytes, manga: MangaCard = None):
        bs = BeautifulSoup(page, "html.parser")

        table = bs.find("table", {"class": "table-chapters"})
        trs = table.find_all('tr')

        items = [tr.findNext('a') for tr in trs]

        links = [item.get('href') for item in items]
        texts = [item.string for item in items]

        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))

    @staticmethod
    def updates_from_page(content):
        bs = BeautifulSoup(content, "html.parser")

        manga_items = bs.find_all("div", {"class": "card"})

        urls = dict()

        for manga_item in manga_items:
            manga_url = manga_item.findNext('a', {'class': 'white-text'}).get('href')

            if manga_url in urls:
                continue

            chapter_url = manga_item.findNext('a', {'class': 'chip'}).get('href')

            urls[manga_url] = chapter_url

        return urls

    async def pictures_from_chapters(self, content: bytes, response=None):
        bs = BeautifulSoup(content, "html.parser")

        ul = bs.find("div", {"id": "pantallaCompleta"})

        images = ul.find_all('img')

        images_url = [quote(img.get('src'), safe=':/%') for img in images]

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
            page += 1

    async def contains_url(self, url: str):
        return url.startswith(self.base_url.geturl())

    async def check_updated_urls(self, last_chapters: List[LastChapter]):

        content = await self.get_url(self.base_url.geturl())

        updates = self.updates_from_page(content)

        updated = [lc.url for lc in last_chapters if updates.get(lc.url) and updates.get(lc.url) != lc.chapter_url]
        not_updated = [lc.url for lc in last_chapters if
                       not updates.get(lc.url) or updates.get(lc.url) == lc.chapter_url]

        return updated, not_updated
