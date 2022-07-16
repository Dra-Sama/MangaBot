import asyncio

import pyrogram.errors


# retries an async awaitable as long as it raises FloodWait, and waits for err.x time
async def retry_on_flood(awaitable):
    while True:
        try:
            return await awaitable
        except pyrogram.errors.FloodWait as err:
            await asyncio.sleep(err.x)
            print(f'FloodWait, waiting {err.x} seconds')
            continue
        except pyrogram.errors.RPCError as err:
            if err.MESSAGE == 'FloodWait':
                await asyncio.sleep(err.x)
                continue
            else:
                raise err
        except Exception as err:
            raise err
