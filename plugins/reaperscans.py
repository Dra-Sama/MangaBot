# By @r4h4t_69

from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote, quote_plus

from bs4 import BeautifulSoup
from plugins.client import MangaClient, MangaCard, MangaChapter, LastChapter

import re

chapters = dict()

class ReaperScansClient(MangaClient):

    base_url = urlparse("https://reaperscans.com")
    search_url = "https://api.reaperscans.com/query"
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
                names.append(manga["title"])
                url.append(f'https://reaperscans.com/series/{manga["series_slug"]}')
                thumb = manga["thumbnail"]
                if not thumb.startswith("https://media.reaperscans.com/"):
                    images.append(f'https://media.reaperscans.com/file/4SRBHm/{thumb}')
                else:
                    images.append(thumb)
                chapters[f'{manga["series_slug"]}'] = manga["free_chapters"]
        mangas = [MangaCard(self, *tup) for tup in zip(names, url, images)]
        
        return mangas

    def chapters_from_page(self, slugs: str, data: bytes, manga: MangaCard = None):
        if slugs in chapters:
            raws = chapters[slugs]
            texts = [chapter["chapter_name"] for chapter in raws]
            links = [f'https://reaperscans.com/series/{slugs}/{chapter["chapter_slug"]}' for chapter in raws]
            return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))
        
        texts = [chapter["chapter_name"] for mangas in data["data"] for chapter in mangas["free_chapters"]]
        links = [f'https://reaperscans.com/series/{slugs}/{chapter["chapter_slug"]}' for mangas in data["data"] for chapter in mangas["free_chapters"]]
        
        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))

    async def updates_from_page(self, content): #### This Fuction Need Further Modification. For Now It Might Not Work ####
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
            for card in cards:
                chapter_url = card.find("li").findNext("a").get("href")
            
            urls[manga_url] = chapter_url

        return urls

    async def pictures_from_chapters(self, data: bytes, response=None):
        content = await response.text()
        soup = BeautifulSoup(content, 'html.parser')
        containers = soup.find_all('div', class_='container')
        images_url = []

        for container in containers:
            imgs = container.find_all('img')
            for img in imgs:
                srcset = img.get('src')
                if srcset:
                    first_srcset = srcset.split(',')[0].strip()
                    url_only = first_srcset.split(' ')[0]

                    if "media.reaperscans.com" in url_only and "jpg" in url_only:
                        cleaned_url = url_only.replace("/_next/image?url=", "").split("&")[0]
                        cleaned_url = cleaned_url.replace("%3A%2F%2F", "://")
                        cleaned_url = cleaned_url.replace("%2Ffile%2F", "/file/")
                        cleaned_url = cleaned_url.replace("%2F", "/")
                        cleaned_url = cleaned_url.replace("%25", "%")

                        images_url.append(cleaned_url)

        return images_url

    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        api_url = "https://api.reaperscans.com/query"
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
