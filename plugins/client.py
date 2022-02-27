import os
from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import List

from aiohttp import ClientSession
from pathlib import Path


@dataclass
class MangaCard:
    client: "MangaClient"
    name: str
    url: str
    picture_url: str

    def unique(self):
        return str(hash(self.url))
    
    
@dataclass
class MangaChapter:
    client: "MangaClient"
    name: str
    url: str
    manga: MangaCard
    pictures: List[str]
    
    def unique(self):
        return str(hash(self.url))


class MangaClient(ClientSession, ABC):

    def __init__(self, *args, name="client", **kwargs):
        if name == "client":
            raise NotImplementedError
        super().__init__(*args, **kwargs)
        self.name = name

    async def get_url(self, file_name, url, *args, cache=False, **kwargs):
        path = Path(f'cache/{self.name}/{file_name}')
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

    async def set_pictures(self, manga_chapter: MangaChapter):
        requests_url = manga_chapter.url
        file_name = f'pictures_{manga_chapter.manga.name}_chapter_{manga_chapter.name}.html'

        content = await self.get_url(file_name, requests_url)

        manga_chapter.pictures = self.pictures_from_chapters(content)

        return manga_chapter

    async def download_pictures(self, manga_chapter: MangaChapter):
        if not manga_chapter.pictures:
            await self.set_pictures(manga_chapter)

        folder_name = f'{manga_chapter.manga.name}/{manga_chapter.name}'
        i = 0
        for picture in manga_chapter.pictures:
            ext = picture.split('.')[-1]
            file_name = f'{folder_name}/{format(i, "05d")}.{ext}'
            await self.get_url(file_name, picture, cache=True)
            i += 1

        return Path(f'cache/{manga_chapter.client.name}') / folder_name

    @abstractmethod
    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        raise NotImplementedError

    @abstractmethod
    async def get_chapters(self, manga_card: MangaCard, page: int = 1) -> List[MangaChapter]:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def pictures_from_chapters(content: bytes):
        raise NotImplementedError
