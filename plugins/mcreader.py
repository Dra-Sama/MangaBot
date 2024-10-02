import re
from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote, quote_plus

from bs4 import BeautifulSoup

from plugins.client import MangaClient, MangaCard, MangaChapter, LastChapter


class MgekoClient(MangaClient):

    base_url = urlparse("https://www.mgeko.cc/")
    search_url = base_url.geturl()
    updates_url = urljoin(base_url.geturl(), "jumbo/manga/")
    search_param = 'search/?search'

    pre_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name="Mgeko", **kwargs):
        super().__init__(*args, name=name, headers=self.pre_headers, **kwargs)

    def mangas_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")

        cards = bs.find_all("li", {"class": "novel-item"})
        
        mangas = [card.findNext('a') for card in cards]
        names = [manga.get("title") for manga in mangas]
        u = "https://www.mgeko.cc"
        url = [u + manga.get("href") for manga in mangas]
        im = "https://cdn.mangageko.com/avatar/288x412"
        images = [im + manga.findNext("img").get("data-src") for manga in mangas]
        #images = []
        
        mangas = [MangaCard(self, *tup) for tup in zip(names, url, images)]

        return mangas

    def chapters_from_page(self, page: bytes, manga: MangaCard = None):
        bs = BeautifulSoup(page, "html.parser")

        ul = bs.find('div', {'id': 'chpagedlist'})
        
        lis = ul.find_all('li')
        
        items = [li.findNext('a') for li in lis]
        a = "https://www.mgeko.cc"
        links = [a + item.get('href') for item in items]
        match = [item.get("title") for item in items]
        texts =  ["Chapter " + str(re.search(r"(\d+(?:\.\d+)?)", tex).group(1)) for tex in match]
        
        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))

    async def updates_from_page(self):
        content = await self.get_url(self.updates_url)
        
        bs = BeautifulSoup(content, "html.parser")
        
        manga_items = bs.find_all("li", {"class": "novel-item"})
        
        urls = dict()
        manga_urls =  [urljoin(self.base_url.geturl(), manga_item.findNext("a").get("href")) for manga_item in manga_items]
        for manga_url in manga_urls:
            cs = await self.get_url(manga_url)

            scrap = BeautifulSoup(cs, "html.parser")
            
            ul = scrap.find('div', {'id': 'chpagedlist'})
            
            lis = ul.find_all('li')
            items = [li.findNext('a') for li in lis]
            a = "https://www.mgeko.cc/"
            links = [a + item.get('href') for item in items][0]
            
            urls[manga_url] = links
            
        return urls

    async def pictures_from_chapters(self, content: bytes, response=None):
        bs = BeautifulSoup(content, "html.parser")

        ul = bs.find("div", {"id": "chapter-reader"})
        
        images = ul.find_all('img')
        
        images_url = [quote(img.get('src'), safe=':/%') for img in images]
        
        return images_url

    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        query = quote_plus(query)

        request_url = self.search_url

        if query:
            #https://www.mgeko.cc/search/?search=One
            request_url += f'search/?search={query}'

        content = await self.get_url(request_url)

        return self.mangas_from_page(content)

    async def get_chapters(self, manga_card: MangaCard, page: int = 1) -> List[MangaChapter]:
        request_url = f'{manga_card.url}'
        
        request_url += "all-chapters/"

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
        updates = await self.updates_from_page()

        updated = []
        not_updated = []
        for lc in last_chapters:
            if lc.url in updates.keys():
                if updates.get(lc.url) != lc.chapter_url:
                    updated.append(lc.url)
            elif updates.get(lc.url) == lc.chapter_url:
                not_updated.append(lc.url)
                
        return updated, not_updated
