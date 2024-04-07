import asyncio
from typing import Callable, Awaitable, Any
from loguru import logger

import pyrogram.errors


# retries an async awaitable as long as it raises FloodWait, and waits for err.x time
def retry_on_flood(function: Callable[[Any], Awaitable]):
    async def wrapper(*args, **kwargs):
        while True:
            try:
                return await function(*args, **kwargs)
            except pyrogram.errors.FloodWait as err:
                logger.warning(f'FloodWait, waiting {err.x} seconds: {err.MESSAGE}')
                await asyncio.sleep(err.x)
                continue
            except pyrogram.errors.RPCError as err:
                if err.MESSAGE == 'FloodWait':
                    logger.warning(f'FloodWait, waiting {err.x} seconds: {err.MESSAGE}')
                    await asyncio.sleep(err.x)
                    continue
                else:
                    raise err
            except Exception as err:
                raise err
    return wrapper
