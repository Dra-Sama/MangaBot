import os
from dataclasses import dataclass
from typing import Optional, List

from aiohttp import ClientSession
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse, urljoin, quote
import re


@dataclass
class ManhuaCard:
    name: str
    url: str
    picture_url: str

    def unique(self):
        return str(hash(self.url))
    
    
@dataclass
class ManhuaChapter:
    name: str
    url: str
    manhua: ManhuaCard
    pictures: List[str]
    
    def unique(self):
        return str(hash(self.url))


class ManhuaKoClient(ClientSession):
    
    base_url = urlparse("https://manhuako.com/")
    search_url = urljoin(base_url.geturl(), "home/search/")
    search_param = 'mq'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    async def get_url(self, file_name, url, *args, cache=False, **kwargs):
        path = Path(f'cache/{file_name}')
        os.makedirs(path.parent, exist_ok=True)
        if cache:
            try:
                content = open(path, 'rb').read()
            except FileNotFoundError:
                response = await self.get(url, *args, **kwargs)
                content = await response.read()
                open(path, 'wb').write(content)
        else:
            response = await self.get(url, *args, **kwargs)
            content = await response.read()
        return content
    
    @staticmethod
    def mangas_from_page(page: bytes):
        bs = BeautifulSoup(page, "html.parser")
    
        cards = bs.find_all("div", {"class": "card"})
    
        manhuas = [card.findNext('a', {'class': 'white-text'}) for card in cards]
        names = [manhua.string for manhua in manhuas]
        url = [manhua.get('href') for manhua in manhuas]
    
        images = [card.findNext('img').get('src') for card in cards]
    
        manhuas = [ManhuaCard(*tup) for tup in zip(names, url, images)]
    
        return manhuas
    
    @staticmethod
    def chapters_from_page(page: bytes, manhua: ManhuaCard = None):
        bs = BeautifulSoup(page, "html.parser")
    
        lis = bs.find_all("li", {"class": "collection-item"})
        
        items = [li.findNext('a') for li in lis]
        
        links = [item.get('href') for item in items]
        texts = [item.string for item in items]
        
        return list(map(lambda x: ManhuaChapter(x[0], x[1], manhua, []), zip(texts, links)))
    
    @staticmethod
    def pictures_from_chapters(content: bytes):
        bs = BeautifulSoup(content, "html.parser")
    
        ul = bs.find("div", {"id": "pantallaCompleta"})
        
        images = ul.find_all('img')
        
        images_url = [quote(img.get('src'), safe=':/') for img in images]
        
        return images_url
    
    async def search(self, query: str = "", page: int = 1):
        query = quote_plus(query)

        request_url = f'{self.search_url}/page/{page}'
        
        if query:
            request_url += f'?{self.search_param}={query}'
        
        file_name = f'search_{query}_page_{page}.html'
        
        content = await self.get_url(file_name, request_url)
        
        return self.mangas_from_page(content)

    async def get_chapters(self, manhua_card: ManhuaCard, page: int = 1) -> List[ManhuaChapter]:
        
        request_url = f'{manhua_card.url}/page/{page}'
        file_name = f'chapters_{manhua_card.name}_page_{page}.html'
        
        content = await self.get_url(file_name, request_url)
        
        return self.chapters_from_page(content, manhua_card)
    
    async def set_pictures(self, manhua_chapter: ManhuaChapter):
        requests_url = manhua_chapter.url
        file_name = f'pictures_{manhua_chapter.manhua.name}_chapter_{manhua_chapter.name}.html'
        
        content = await self.get_url(file_name, requests_url)
        
        manhua_chapter.pictures = self.pictures_from_chapters(content)
        
        return manhua_chapter
    
    async def download_pictures(self, manhua_chapter: ManhuaChapter):
        if not manhua_chapter.pictures:
            await self.set_pictures(manhua_chapter)
        
        folder_name = f'{manhua_chapter.manhua.name}/{manhua_chapter.name}'
        i = 0
        for picture in manhua_chapter.pictures:
            ext = picture.split('.')[-1]
            file_name = f'{folder_name}/{format(i, "05d")}.{ext}'
            await self.get_url(file_name, picture, cache=True)
            i += 1
            
        return Path('cache') / folder_name
