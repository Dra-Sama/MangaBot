#THis Code is made by Wizard Bots on telegram
# t.me/Wizard_Bots

import json
from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote, quote_plus

from bs4 import BeautifulSoup
import requests

from plugins.client import MangaClient, MangaCard, MangaChapter, LastChapter


class ComickClient(MangaClient):

    base_url = urlparse("https://comick.io/")
    search_url = base_url.geturl()
    search_param = 'search'
    updates_url = base_url.geturl()

    pre_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name="Comick", **kwargs):
        super().__init__(*args, name=name, headers=self.pre_headers, **kwargs)

    
    def mangas_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")

        container = bs.find("div", {"class": " w-full h-full relative"})

        if container is not None:
            cards = container.find_all("div", {"class": "cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 flex w-full pb-1 min-w-0"})
            if cards:
                for card in cards:
                    mangas = [card.findNext('a') for card in cards]
                    names = [manga.findNext("img").get("alt") for manga in mangas]
                    url = [f'https://comick.io/{manga.get("href")}' for manga in mangas]
                    images = [manga.findNext("img").get("src") for manga in mangas]
                    
                    mangas = [MangaCard(self, *tup) for tup in zip(names, url, images)]
                    
   
        else:
            response = requests.get(page)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                script_text = soup.find('script', {'id': '__NEXT_DATA__'}).get_text(strip=True)
                jsoncode = json.loads(script_text)
                data = jsoncode.get("props" and "pageProps")
                extras = {item['md_genres']['group']: [d['md_genres']['name'] for d in data['comic']['md_comic_md_genres'] if d.get('md_genres', {}).get('group') == item['md_genres']['group']] for item in data['comic']['md_comic_md_genres']}
                cards = data
                if cards:
                    for card in cards:
                        mangas = [card.findNext('a') for card in cards]
                        for manga in mangas:
                            names = data['comic']['title']
                            url = [f'https://comick.io/{manga.get("href")}' for manga in mangas]
                            images = f'https://meo3.comick.pictures/{data["comic"]["md_covers"][0]["b2key"]}'
                            mangas = [MangaCard(self, *tup) for tup in zip(names, url, images)]
        return mangas

    def chapters_from_page(self, page: bytes, manga: MangaCard = None):
        bs = BeautifulSoup(page, "html.parser")

        container = bs.find("div", {"id": "chapterlist"})

        lis = container.find_all("tr")

        items = [li.findNext('a') for li in lis]

        links = [item.get("href") for item in items]
        texts = [item.findChild(name='title', attrs={'class': 'font-semibold'}).string.strip() for item in items]

        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))


    def updates_from_page(self, content):
        bs = BeautifulSoup(content, "html.parser")

        container = bs.find("ul", {"class": "homeupdate"})

        manga_items = container.find_all("li")

        urls = dict()

        for manga_item in manga_items[:20]:
            manga_url = manga_item.findNext("a").get("href")

            if manga_url in urls:
                continue

            chapter_url = manga_item.findNext("dl").findNext("a").get("href")

            urls[manga_url] = chapter_url

        return urls

    async def pictures_from_chapters(self, content: bytes, response=None):
        bs = BeautifulSoup(content, "html.parser")
        
        container = bs.find('script', {'id': '__NEXT_DATA__'})
        
        images = json.loads(container.get_text(strip=True))['props']['pageProps']['chapter']['md_images']
        
        images_url = [f'https://meo3.comick.pictures/{image["b2key"]}' for image in images]

        return images_url

    

    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        request_url = self.search_url

        if query:
            request_url = f'{request_url}?{self.search_param}={quote_plus(query)}'

        content = await self.get_url(request_url)

        return self.mangas_from_page(content)[(page - 1) * 20:page * 20]

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

        content = await self.get_url(self.home_page)

        updates = self.updates_from_page(content)

        updated = [lc.url for lc in last_chapters if updates.get(lc.url) and updates.get(lc.url) != lc.chapter_url]
        not_updated = [lc.url for lc in last_chapters if not updates.get(lc.url)
                       or updates.get(lc.url) == lc.chapter_url]

        return updated, not_updated
