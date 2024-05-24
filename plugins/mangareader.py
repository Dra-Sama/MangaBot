#THis Code is made by Wizard Bots on telegram
# t.me/Wizard_Bots

from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote, quote_plus

from bs4 import BeautifulSoup

from plugins.client import MangaClient, MangaCard, MangaChapter, LastChapter


class MangaReaderClient(MangaClient):

    base_url = urlparse("https://mangareader.to/")
    search_url = base_url.geturl()
    search_param = 'search'
    updates_url = base_url.geturl()

    pre_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name="MangaReader", **kwargs):
        super().__init__(*args, name=name, headers=self.pre_headers, **kwargs)

    def mangas_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")

        container = bs.find("div", {"class": "item item-spc"})

        cards = container.find_all("div", {"class": "manga-poster"})

        mangas = [card.findNext('a') for card in cards]
        names = [manga.get('title') for manga in mangas]
        url = [manga.get("href") for manga in mangas]
        images = [manga.findNext("img").get("src") for manga in mangas]

        mangas = [MangaCard(self, *tup) for tup in zip(names, url, images)]

        return mangas

    def chapters_from_page(self, page: bytes, manga: MangaCard = None):
        bs = BeautifulSoup(page, "html.parser")

        ul = bs.find('ul', {'id': 'chapter-list'})

        lis = ul.findAll('li')
        a_elems = [li.find('a') for li in lis]

        links = [urljoin(self.base_url.geturl(), a.get('href')) for a in a_elems]
        texts = [a.findNext('data-number', {'class': 'item reading-item chapter-item'}).text.strip() for a in a_elems]

        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))

    def updates_from_page(self, content):
        bs = BeautifulSoup(content, "html.parser")

        manga_items = bs.find_all("div", {"class": "utao"})

        urls = dict()

        for manga_item in manga_items:
            manga_url = manga_item.findNext("a").get("href")

            if manga_url in urls:
                continue

            chapter_url = manga_item.findNext("ul").findNext("a").get("href")

            urls[manga_url] = chapter_url

        return urls

    async def pictures_from_chapters(self, content: bytes, response=None):
        bs = BeautifulSoup(content, "html.parser")

        container = bs.find("div", {"id": "readerarea"})

        images = container.find_all("p")

        images_url = [quote(img.get('src'), safe=':/%') for img in images]

        return images_url

    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        query = quote_plus(query)

        request_url = self.search_url

        if query:
            request_url += f'{self.search_param}?keyword={query}'

        content = await self.get_url(request_url)

        return self.mangas_from_page(content)

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

        content = await self.get_url(self.updates_url)

        updates = self.updates_from_page(content)

        updated = [lc.url for lc in last_chapters if updates.get(lc.url) and updates.get(lc.url) != lc.chapter_url]
        not_updated = [lc.url for lc in last_chapters if
                       not updates.get(lc.url) or updates.get(lc.url) == lc.chapter_url]

        return updated, not_updated
