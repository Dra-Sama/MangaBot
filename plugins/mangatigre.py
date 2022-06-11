import json
from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote, quote_plus

from aiohttp import ClientResponse
from bs4 import BeautifulSoup
from bs4.element import PageElement

from plugins.client import MangaClient, MangaCard, MangaChapter, LastChapter


class MangatigreClient(MangaClient):

    base_url = urlparse("https://www.mangatigre.net/")
    search_url = urljoin(base_url.geturl(), 'mangas/search')
    manga_url = urljoin(base_url.geturl(), 'manga')
    img_url = urlparse("https://i2.mtcdn.xyz/")
    cover_url = urljoin(img_url.geturl(), "mangas")
    search_param = 'query'

    pre_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name="Mangatigre", **kwargs):
        super().__init__(*args, name=name, headers=self.pre_headers, **kwargs)

    def mangas_from_page(self, page: bytes):
        dt = json.loads(page)
        mangas = dt['result']

        names = [manga.get('name') for manga in mangas]
        url = [f"{self.manga_url}/{manga.get('slug')}" for manga in mangas]
        images = [f"{self.cover_url}/{manga.get('image')}" for manga in mangas]

        mangas = [MangaCard(self, *tup) for tup in zip(names, url, images)]

        return mangas

    def chapters_from_page(self, page: bytes, manga: MangaCard = None):
        bs = BeautifulSoup(page, "html.parser")

        ul = bs.find('ul', {'class': 'list-unstyled'})
        lis = ul.find_all("li")

        items = [li.findNext('a') for li in lis]

        links = [item.get('href') for item in items]
        texts = [item.get('title').split(':')[0] for item in items]

        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))

    def updates_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")

        manga_items: List[PageElement] = bs.find_all("article", {"class": "chapter-block"})

        urls = dict()

        for manga_item in manga_items:

            manga_url = manga_item.findNext('a').get('href')

            chapter_item = manga_item.findNext("div", {"class": "chapter"})
            chapter_url = chapter_item.findNext("a").get('href')

            urls[manga_url] = chapter_url

        return urls

    async def pictures_from_chapters(self, content: bytes, response: ClientResponse = None):
        bs = BeautifulSoup(content, "html.parser")

        btn = bs.find('button', {'data-read-type': 2})
        if btn:
            token = btn.get('data-token')

            data = {
                '_method': 'patch',
                '_token': token,
                'read_type': 2
            }

            content = await self.get_url(f'{response.url}/read-type', data=data, method='post')
            bs = BeautifulSoup(content, "html.parser")

        ul = bs.find("div", {"class": "display-zone"})

        images = ul.find_all('img')
        images = [f"https:{img.get('data-src') or img.get('src')}" for img in images]

        images_url = [quote(img, safe=':/%') for img in images]

        return images_url

    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        main_page = await self.get_url(self.base_url.geturl())

        bs = BeautifulSoup(main_page, "html.parser")
        div = bs.find('div', {'class': 'input-group'})
        token = div.find('input').get('data-csrf')

        request_url = self.search_url

        data = {
            self.search_param: query,
            '_token': token
        }

        content = await self.get_url(request_url, data=data, method='post')

        return self.mangas_from_page(content)[(page - 1) * 20:page * 20]

    async def get_chapters(self, manga_card: MangaCard, page: int = 1) -> List[MangaChapter]:
        chapters = [x async for x in self.iter_chapters(manga_card.url, manga_card.name)]
        return chapters[(page - 1) * 20:page * 20]

    async def iter_chapters(self, manga_url: str, manga_name) -> AsyncIterable[MangaChapter]:
        manga_card = MangaCard(self, manga_name, manga_url, '')

        request_url = f'{manga_card.url}'

        chapter_page = await self.get_url(request_url)

        bs = BeautifulSoup(chapter_page, "html.parser")
        btn = bs.find('button', {'class': 'btn-load-more-chapters'})
        token = btn.get('data-token')

        data = {'_token': token}

        content = await self.get_url(request_url, data=data, method='post')

        chapters = self.chapters_from_page(content, manga_card)

        for chapter in chapters:
            yield chapter

    async def contains_url(self, url: str):
        return url.startswith(self.base_url.geturl())

    async def check_updated_urls(self, last_chapters: List[LastChapter]):

        content = await self.get_url(self.base_url.geturl())

        updates = self.updates_from_page(content)

        updated = [lc.url for lc in last_chapters if updates.get(lc.url) and updates.get(lc.url) != lc.chapter_url]
        not_updated = [lc.url for lc in last_chapters if not updates.get(lc.url) or updates.get(lc.url) == lc.chapter_url]

        return updated, not_updated