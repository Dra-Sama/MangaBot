import os
from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import List, AsyncIterable

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

    async def get_url(self, url, *args, file_name=None, cache=False, method='get', data=None, **kwargs):
        if cache:
            path = Path(f'cache/{self.name}/{file_name}')
            os.makedirs(path.parent, exist_ok=True)
            try:
                content = open(path, 'rb').read()
            except FileNotFoundError:
                if method == 'get':
                    response = await self.get(url, *args, **kwargs)
                elif method == 'post':
                    response = await self.post(url, data=data or {}, **kwargs)
                else:
                    raise ValueError
                content = await response.read()
                open(path, 'wb').write(content)
        else:
            if method == 'get':
                response = await self.get(url, *args, **kwargs)
            elif method == 'post':
                response = await self.post(url, data=data or {}, **kwargs)
            else:
                raise ValueError
            content = await response.read()
        return content

    async def set_pictures(self, manga_chapter: MangaChapter):
        requests_url = manga_chapter.url

        content = await self.get_url(requests_url)

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
            await self.get_url(picture, file_name=file_name, cache=True)
            i += 1

        return Path(f'cache/{manga_chapter.client.name}') / folder_name

    @abstractmethod
    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        raise NotImplementedError

    @abstractmethod
    async def get_chapters(self, manga_card: MangaCard, page: int = 1) -> List[MangaChapter]:
        raise NotImplementedError

    @abstractmethod
    async def contains_url(self, url: str):
        raise NotImplementedError

    @abstractmethod
    async def iter_chapters(self, manga_url: str) -> AsyncIterable[MangaChapter]:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def pictures_from_chapters(content: bytes):
        raise NotImplementedError
