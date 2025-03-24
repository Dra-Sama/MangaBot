#THis Code is made by Wizard Bots on telegram
# t.me/Wizard_Bots

from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote, quote_plus
import re

from bs4 import BeautifulSoup
from bs4.element import PageElement

from plugins.client import MangaClient, MangaCard, MangaChapter, LastChapter


class ManhwaClanClient(MangaClient):

    base_url = urlparse("https://manhwaclan.com/")
    search_url = base_url.geturl()
    updates_url = base_url.geturl()


    pre_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name="ManhwaClan", **kwargs):
        super().__init__(*args, name=name, headers=self.pre_headers, **kwargs)

    def mangas_from_page(self, page: bytes):
      bs = BeautifulSoup(page, "html.parser")
      
      con = bs.find(class_="tab-content-wrap")
      cards = con.find_all(class_="tab-thumb c-image-hover")
      
      mangas = [card.findNext('a') for card in cards]
      
      names = [manga.findNext("img").get("alt") for manga in mangas]
      url = [manga.get("href") for manga in mangas]
      images = [manga.findNext("img").get("src") for manga in mangas]
      
      mangas = [MangaCard(self, *tup) for tup in zip(names, url, images)]
      
      return mangas
    
    def chapters_from_page(self, page: bytes, manga: MangaCard = None):
        bs = BeautifulSoup(page, "html.parser")
        
        con = bs.find(class_="page-content-listing single-page")
        
        cards = con.find_all("li")
        
        mangas = [card.findNext('a') for card in cards]
        
        texts = [manga.string.strip() for manga in mangas]
        
        links = [manga.get("href") for manga in mangas]
        
        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))

    async def updates_from_page(self):
        page = await self.get_url(self.updates_url)
        
        bs = BeautifulSoup(page, "html.parser")
        
        con = bs.find(class_="c-blog__content")
        
        cards = con.find_all(class_="col-6 col-md-3 badge-pos-1")
        
        urls = dict()
        for card in cards:
            manga_url = card.find("a")["href"]
            
            data = card.findNext("span")
            
            chapter_url = data.findNext("a")["href"]
            
            urls[manga_url] = chapter_url
        
        return urls

    async def pictures_from_chapters(self, content: bytes, response=None):
        bs = BeautifulSoup(content, "html.parser")
        
        cards = bs.find_all(class_="page-break no-gaps")
        
        mangas = [card.findNext('img') for card in cards]
        
        images_url = [manga.get("src").strip() for manga in mangas]
        
        return images_url

    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
      query = quote_plus(query)
      
      request_url = f"https://manhwaclan.com/?s={query}&post_type=wp-manga"
      
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
