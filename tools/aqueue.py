import asyncio
from typing import List, Tuple, Any, Set


class AQueue:
    def __init__(self, maxsize=None):
        self._queue = []  # type: List[Tuple[Any, int]]
        self._mask = set()  # type: Set[int]
        self._put_lock = asyncio.Lock()
        self._get_lock = asyncio.Lock()
        self._not_empty = asyncio.Event()

    async def put(self, item: Any, lock: int):
        async with self._put_lock:
            self._queue.append((item, lock))
            if lock not in self._mask:
                self._not_empty.set()

    async def get(self, worker_id):
        async with self._get_lock:
            await self._not_empty.wait()
            available = [i for i, (_, i_lock) in enumerate(self._queue) if i_lock not in self._mask]
            item, lock = self._queue.pop(available[0])
            self.acquire(lock)
            available = [i for i, (_, i_lock) in enumerate(self._queue) if i_lock not in self._mask]
            if not available:
                self._not_empty.clear()
            return item, lock

    def acquire(self, lock: int):
        self._mask.add(lock)

    def release(self, lock: int):
        self._mask.remove(lock)
        for _, i_lock in self._queue:
            if i_lock == lock:
                self._not_empty.set()
                break

    def qsize(self):
        return len(self._queue)

    def empty(self):
        return not self._queue
