from dataclasses import dataclass

from pyrogram.types import Message

from manhuako import ManhuaCard


class Pagination:
    pagination_id: int = 0
    
    def __init__(self):
        self.id = self.pagination_id
        Pagination.pagination_id += 1
        self.page = 1
        self.message: Message = None
        self.manhua: ManhuaCard = None
