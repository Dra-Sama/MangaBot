import os

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, Field, Session
from sqlmodel.ext.asyncio.session import AsyncSession

from tools import Singleton


class ChapterFile(SQLModel, table=True):
    url: str = Field(primary_key=True)
    file_id: str


class DB(metaclass=Singleton):
    
    def __init__(self):
        dbname = os.getenv('DATABASE_URL')
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
