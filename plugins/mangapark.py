from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote, quote_plus 

import json
import re 

from bs4 import BeautifulSoup
from bs4.element import PageElement

from plugins.client import MangaClient, MangaCard, MangaChapter, LastChapter


class MangaParkClient(MangaClient):

    base_url = urlparse("https://mangapark.net")
    search_url = base_url.geturl()
    search_param = 'searchword'
    updates_url = urljoin(base_url.geturl(), "/search")


    pre_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name="MangaPark", **kwargs):
        super().__init__(*args, name=name, headers=self.pre_headers, **kwargs)

    def mangas_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")
        
        cards = bs.find_all("div", {"class": "group relative w-full"})
        
        mangas = [card.findNext('a') for card in cards]
        names = [manga.findNext("img").get('title') for manga in mangas]
        url = [self.search_url + manga.get("href") for manga in mangas]
        images = [manga.findNext("img").get("src") for manga in mangas]

        mangas = [MangaCard(self, *tup) for tup in zip(names, url, images)]

        return mangas
    
    def chapters_from_page(self, page: bytes, manga: MangaCard = None):
        bs = BeautifulSoup(page, "html.parser")
        
        lis = bs.find_all("a", {"class": "link-hover link-primary visited:text-accent"})
        items = [li.findNext('a') for li in lis]
        
        url = "https://mangapark.net"
        urls = [item.get("href") for item in items]
        links = []
        for i in urls:
            if '/title' in i:
                chapter_url = url + i
                if chapter_url.split('/')[5] != "mplists?sortby=likes":
                    links.append(chapter_url)
                    
        names = [sub.split('/')[5] for sub in links]
        texts = [re.sub('^\d+', '', s).replace('-', ' ') for s in names]
    
        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))
        
    async def updates_from_page(self):
        page = await self.get_url(self.updates_url)
        
        bs = BeautifulSoup(page, "html.parser")

        manga_items = bs.find_all("h3", {"class": "font-bold space-x-1"})
        chapter_items = bs.find_all("span", {"class": "line-clamp-1 space-x-1 grow"})
        
        urls = dict()
        for manga_item in manga_items:
            manga_url = urljoin(self.base_url.geturl(), manga_item.findNext("a").get("href"))
            if manga_url in urls:
                continue
            for chapter_item in chapter_items:
                chapter_url = urljoin(self.base_url.geturl(), chapter_item.findNext("a").get("href"))
                curl = chapter_url.split('/')[4]
                murl = manga_url.split('/')[4]
                if curl == murl:
                    urls[manga_url] = chapter_url 
                    
        return urls

    async def pictures_from_chapters(self, content: bytes, response=None):
        bs = BeautifulSoup(content, "html.parser")
        
        lis = bs.find("script", {"type": "qwik/json"})
        
        rdata = lis.string.strip()
        data = json.loads(rdata)
        cdata = data["objs"]
        # https://s01.mpqom.org/media/2002/f73/67396f42399723009ef1937f/60561643_720_9574_457032.jpeg
        pattern = r"https://s[^ ]+"
        images_url = [quote(i.lstrip(), safe=':/%') for i in cdata if re.search(pattern, str(i))]
    
        return images_url

    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        query = quote_plus(query)

        request_url = self.search_url

        if query:
          #https://mangapark.net/search?word=One%20Piece
            request_url += f"/search?word={query}"

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
