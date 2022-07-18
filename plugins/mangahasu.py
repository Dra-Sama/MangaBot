from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote, quote_plus

from bs4 import BeautifulSoup

from models import LastChapter
from plugins.client import MangaClient, MangaCard, MangaChapter


class MangaHasuClient(MangaClient):
    base_url = urlparse("https://mangahasu.se/")
    search_url = urljoin(base_url.geturl(), "search/autosearch")
    search_param = 'key'

    pre_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name="MangaHasu", **kwargs):
        super().__init__(*args, name=name, headers=self.pre_headers, **kwargs)

    def mangas_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")

        cards = bs.find_all("li")[:-1]

        mangas = [card.a for card in cards]
        names = [manga.findNext('p', {'class': 'name'}).text.strip() for manga in mangas]
        url = [manga.get('href').strip() for manga in mangas]
        images = [manga.find("img").get('src').strip() for manga in mangas]

        mangas = [MangaCard(self, *tup) for tup in zip(names, url, images)]

        return mangas

    def chapters_from_page(self, page: bytes, manga: MangaCard = None):
        bs = BeautifulSoup(page, "html.parser")

        div = bs.find("div", {"class": "list-chapter"})

        lis = div.findAll('tr')[1:]
        a_elems = [li.find('a') for li in lis]

        links = [a.get('href') for a in a_elems]
        texts = [(a.text if not a.text.startswith(manga.name) else a.text[len(manga.name):]).strip() for a in a_elems]

        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))

    def updates_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")

        div = bs.find('div', {'class': 'st_content'})

        manga_items = div.find_all('div', {'class': 'info-manga'})

        urls = dict()

        for manga_item in manga_items:

            manga_url = manga_item.findNext('a',  {"class": "name-manga"}).get('href')

            chapter_item = manga_item.findNext("a", {"class": "name-chapter"})
            if not chapter_item:
                continue
            chapter_url = chapter_item.get('href')

            if manga_url not in urls:
                urls[manga_url] = chapter_url

        return urls

    async def pictures_from_chapters(self, content: bytes, response=None):
        bs = BeautifulSoup(content, "html.parser")

        div = bs.find('div', {'class': 'img'})

        imgs = div.findAll('img')

        images_url = [quote(img.get('src'), safe=':/%') for img in imgs]

        return images_url

    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        request_url = self.search_url

        data = {
            self.search_param: query
        }

        content = await self.get_url(request_url, data=data, method='post')

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

        content = await self.get_url(self.base_url.geturl())

        updates = self.updates_from_page(content)

        updated = [lc.url for lc in last_chapters if updates.get(lc.url) and updates.get(lc.url) != lc.chapter_url]
        not_updated = [lc.url for lc in last_chapters if not updates.get(lc.url)
                       or updates.get(lc.url) == lc.chapter_url]

        return updated, not_updated
