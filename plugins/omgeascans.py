from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote, quote_plus

from bs4 import BeautifulSoup

from plugins.client import MangaClient, MangaCard, MangaChapter, LastChapter
import re

chapters = dict()

class OmgeaScansClient(MangaClient):

    base_url = urlparse("https://omegascans.org")
    search_url = "https://api.omegascans.org/query"
    updates_url = base_url.geturl()

    pre_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name="ReaperScans", **kwargs):
        super().__init__(*args, name=name, headers=self.pre_headers, **kwargs)

    def mangas_from_page(self, data):
        names = []
        url = []
        images = []
        if data["meta"]["total"] > 0:
            for manga in data["data"]:
                names.append(manga["title"]) #for manga in data["data"][:100]]
                url.append(f'https://omegascans.org/series/{manga["series_slug"]}') # for manga in data["data"][:100]]
                thumb = manga["thumbnail"]
                if not thumb.startswith("https://media.omegascans.org/file"):
                    images.append(f'https://media.omegascans.org/file/4SRBHm{thumb}') #for manga in data["data"][:100]]
                else:
                    images.append(thumb)
                chapters[f'{manga["series_slug"]}'] = manga["free_chapters"]
        
        mangas = [MangaCard(self, *tup) for tup in zip(names, url, images)]
        
        return mangas

    def chapters_from_page(self, slugs: str, data: bytes, manga: MangaCard = None):
        if slugs in chapters:
            raws = chapters[slugs]
            texts = [chapter["chapter_name"] for chapter in raws]
            links = [f'https://omegascans.org/series/{slugs}/{chapter["chapter_slug"]}' for chapter in raws]
            return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))
        
        texts = [chapter["chapter_name"] for mangas in data["data"] for chapter in mangas["free_chapters"]]
        links = [f'https://omegascans.org/series/{slugs}/{chapter["chapter_slug"]}' for mangas in data["data"] for chapter in mangas["free_chapters"]]
        
        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))

    async def updates_from_page(self, content):
        bs = BeautifulSoup(content, "html.parser")

        manga_items = bs.find_all("div", {"class": "bs"})

        urls = dict()

        for manga_item in manga_items:
            manga_url = manga_item.findNext("a").get("href")
            
            if manga_url in urls:
                continue
            
            data = await self.get_url(manga_url)
            bs = BeautifulSoup(data.text, "html.parser")
            cards = bs.find("div", {"class": "eplister"})
            for card in cards: chapter_url = card.find("li").findNext("a").get("href")
            
            urls[manga_url] = chapter_url

        return urls

    async def pictures_from_chapters(self, data: bytes, response=None):
        soup = BeautifulSoup(data, 'html.parser')
        img_tags = soup.find_all('img')
        
        images_url = []
        for img in img_tags:
            img_url = img.get('data-src') if img.get('data-src') else img.get('src')
            if "media.omegascans.org" in img_url and "uploads" in img_url:
                images_url.append(img_url)
        
        return images_url

    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        api_url = "https://api.omegascans.org/query"
        search_param = {"adult": "true", "query_string": query}
        
        data = await self.get_url(api_url, params=search_param, rjson=True)
        
        return self.mangas_from_page(data)

    async def get_chapters(self, manga_card: MangaCard, page: int = 1) -> List[MangaChapter]:
        urls = str(manga_card.url)
        slugs = urls.split("/")[4]
        
        query = slugs.replace("-", " ")
        search_param = {"adult": "true", "query_string": query}
  
        data = await self.get_url(self.search_url, params=search_param, rjson=True)
        
        return self.chapters_from_page(slugs, data, manga_card)[(page - 1) * 20:page * 20]

    async def iter_chapters(self, manga_url: str, manga_name) -> AsyncIterable[MangaChapter]:
        manga_card = MangaCard(self, manga_name, manga_url, '')

        urls = str(manga_card.url)
        slugs = urls.split("/")[4]
        
        query = slugs.replace("-", " ")
        search_param = {"adult": "true", "query_string": query}
  
        data = await self.get_url(self.search_url, params=search_param, rjson=True)

        for chapter in self.chapters_from_page(slugs, data, manga_card):
            yield chapter

    async def contains_url(self, url: str):
        return url.startswith(self.base_url.geturl())

    async def check_updated_urls(self, last_chapters: List[LastChapter]):
        content = await self.get_url(self.updates_url)

        updates = await self.updates_from_page(content)

        updated = []
        not_updated = []
        for lc in last_chapters:
            if lc.url in updates.keys():
                if updates.get(lc.url) != lc.chapter_url:
                    updated.append(lc.url)
            elif updates.get(lc.url) == lc.chapter_url:
                not_updated.append(lc.url)
                
        return updated, not_updated
