from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote

from bs4 import BeautifulSoup

from plugins.client import MangaClient, MangaCard, MangaChapter, LastChapter


class ManganeloClient(MangaClient):

    base_url = urlparse("https://m.manganelo.com/")
    search_url = urljoin(base_url.geturl(), "search/story/")
    updates_url = urljoin(base_url.geturl(), "genre-all-update-latest")
    chapter_url = "https://chapmanganelo.com/"

    pre_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name="Manganelo", **kwargs):
        super().__init__(*args, name=name, headers=self.pre_headers, **kwargs)

    def mangas_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")

        cards = bs.find_all("div", {"class": "search-story-item"})

        mangas = [card.findNext('a') for card in cards]
        names = [manga.get('title') for manga in mangas]
        url = [manga.get("href") for manga in mangas]
        images = [manga.findNext("img").get("src") for manga in mangas]

        mangas = [MangaCard(self, *tup) for tup in zip(names, url, images)]

        return mangas

    def chapters_from_page(self, page: bytes, manga: MangaCard = None):
        bs = BeautifulSoup(page, "html.parser")

        lis = bs.find_all("li", {"class": "a-h"})

        items = [li.findNext('a') for li in lis]

        links = [item.get("href") for item in items]
        texts = [item.string for item in items]

        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))

    def updates_from_page(self, content):
        bs = BeautifulSoup(content, "html.parser")

        manga_items = bs.find_all("div", {"class": "content-genres-item"})

        urls = dict()

        for manga_item in manga_items:
            manga_url = manga_item.findNext("a", {"class": "genres-item-img"}).get("href")

            if manga_url in urls:
                continue

            chapter_url = manga_item.findNext('a', {'class': 'genres-item-chap'}).get('href')

            urls[manga_url] = chapter_url

        return urls

    async def pictures_from_chapters(self, content: bytes, response=None):
        bs = BeautifulSoup(content, "html.parser")

        ul = bs.find("div", {"class": "container-chapter-reader"})

        images = ul.find_all('img')

        images_url = [quote(img.get('src'), safe=':/%') for img in images]

        return images_url

    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        query = quote(query.replace(' ', '_').lower())

        request_url = f'{self.search_url}'

        if query:
            request_url += f'{query}'

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

    def get_picture(self, manga_chapter: MangaChapter, url, *args, **kwargs):
        headers = dict(self.headers)
        headers['Referer'] = self.chapter_url

        return self.get_url(url, headers=headers, *args, **kwargs)

    async def contains_url(self, url: str):
        return url.startswith(self.base_url.geturl()) or url.startswith(self.chapter_url)

    async def check_updated_urls(self, last_chapters: List[LastChapter]):

        content = await self.get_url(self.updates_url)

        updates = self.updates_from_page(content)

        updated = [lc.url for lc in last_chapters if updates.get(lc.url) and updates.get(lc.url) != lc.chapter_url]
        not_updated = [lc.url for lc in last_chapters if
                       not updates.get(lc.url) or updates.get(lc.url) == lc.chapter_url]

        return updated, not_updated
