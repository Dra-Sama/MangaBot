import os
from typing import Type, List, TypeVar

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, Field, Session, select
from sqlmodel.ext.asyncio.session import AsyncSession

from tools import Singleton

T = TypeVar("T")


class ChapterFile(SQLModel, table=True):
    url: str = Field(primary_key=True)
    file_id: str


class Subscription(SQLModel, table=True):
    url: str = Field(primary_key=True)
    user_id: str = Field(primary_key=True, regex=r'\d+')


class LastChapter(SQLModel, table=True):
    url: str = Field(primary_key=True)
    chapter_url: str = Field


class MangaName(SQLModel, table=True):
    url: str = Field(primary_key=True)
    name: str = Field


class DB(metaclass=Singleton):
    
    def __init__(self):
        dbname = os.getenv('DATABASE_URL_PRIMARY') or os.getenv('DATABASE_URL')
        if dbname.startswith('postgres://'):
            dbname = dbname.replace('postgres://', 'postgresql+asyncpg://', 1)
        if dbname.startswith('sqlite'):
            dbname = dbname.replace('sqlite', 'sqlite+aiosqlite', 1)
    
        self.engine = create_async_engine(dbname)
        
    async def connect(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all, checkfirst=True)

    async def add(self, other: SQLModel):
        async with AsyncSession(self.engine) as session:  # type: AsyncSession
            async with session.begin():
                session.add(other)

    async def get(self, table, id):
        async with AsyncSession(self.engine) as session:  # type: AsyncSession
            return await session.get(table, id)

    async def get_all(self, table: Type[T]) -> List[T]:
        async with AsyncSession(self.engine) as session:  # type: AsyncSession
            statement = select(table)
            return await session.exec(statement=statement)

    async def erase(self, other: SQLModel):
        async with AsyncSession(self.engine) as session:  # type: AsyncSession
            async with session.begin():
                await session.delete(other)
