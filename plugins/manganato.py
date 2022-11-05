import json
from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote
import re

from bs4 import BeautifulSoup
from bs4.element import PageElement

from plugins.client import MangaClient, MangaCard, MangaChapter, LastChapter


class ManganatoClient(MangaClient):

    base_url = urlparse("https://manganato.com/")
    search_url = urljoin(base_url.geturl(), 'getstorysearchjson')
    search_param = 'searchword'
    read_url = 'https://readmanganato.com/'
    chap_url = 'https://chapmanganato.com/'

    pre_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name="Manganato", **kwargs):
        super().__init__(*args, name=name, headers=self.pre_headers, **kwargs)

    def mangas_from_page(self, page: bytes):
        li = json.loads(page)

        pattern = re.compile(r'<span .*?>(.+?)</span>')

        items = li['searchlist']
        names = []
        for item in items:
            name = item['name']
            while '</span>' in name:
                name = re.sub(pattern, r'\1', name)
            names.append(name.title())

        url = [item['url_story'] for item in items]
        images = [item['image'] for item in items]

        mangas = [MangaCard(self, *tup) for tup in zip(names, url, images)]

        return mangas

    def chapters_from_page(self, page: bytes, manga: MangaCard = None):
        bs = BeautifulSoup(page, "html.parser")

        lis = bs.find_all("li", {"class": "a-h"})

        items = [li.findNext('a') for li in lis]

        links = [item.get('href') for item in items]
        texts = [item.string.strip() for item in items]

        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))

    def updates_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")

        manga_items: List[PageElement] = bs.find_all("div", {"class": "content-homepage-item"})

        urls = dict()

        for manga_item in manga_items:

            manga_url = manga_item.findNext('a').get('href')

            chapter_item = manga_item.findNext("p", {"class": "a-h item-chapter"})
            if not chapter_item:
                continue
            chapter_url = chapter_item.findNext("a").get('href')

            urls[manga_url] = chapter_url

        return urls

    async def pictures_from_chapters(self, content: bytes, response=None):
        bs = BeautifulSoup(content, "html.parser")

        ul = bs.find("div", {"class": "container-chapter-reader"})

        images = ul.find_all('img')

        images_url = [quote(img.get('src'), safe=':/%') for img in images]

        return images_url

    async def get_picture(self, manga_chapter: MangaChapter, url, *args, **kwargs):
        pattern = re.compile(r'(.*\.com/)')
        match = re.match(pattern, manga_chapter.url)
        referer = match.group(1)

        headers = dict(self.headers)
        headers['Referer'] = referer

        return await super(ManganatoClient, self).get_picture(manga_chapter, url, headers=headers, *args, **kwargs)

    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        query = query.lower().replace(' ', '_')

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
        return url.startswith(self.read_url) or url.startswith(self.base_url.geturl()) or url.startswith(self.chap_url)

    async def check_updated_urls(self, last_chapters: List[LastChapter]):

        content = await self.get_url(self.base_url.geturl())

        updates = self.updates_from_page(content)

        updated = [lc.url for lc in last_chapters if updates.get(lc.url) and updates.get(lc.url) != lc.chapter_url]
        not_updated = [lc.url for lc in last_chapters if not updates.get(lc.url)
                       or updates.get(lc.url) == lc.chapter_url]

        return updated, not_updated
