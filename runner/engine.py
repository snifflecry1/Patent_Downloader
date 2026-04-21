import asyncio
import json
import logging

import aiofiles
from aiohttp import ClientSession

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, limit):
        self.interval = 60 / limit
        self.lock = asyncio.Lock()
        self.last_call = 0

    # Need to ensure requests per second are within defined rate limits for api
    async def acquire_lock(self):
        async with self.lock:
            now = asyncio.get_running_loop().time()
            wait = self.interval - (now - self.last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self.last_call = asyncio.get_running_loop().time()


async def fetch_worker(
    id, page_queue: asyncio.Queue, write_queue: asyncio.Queue, session, client, limiter
):
    while True:
        page_num = await page_queue.get()
        try:
            logger.info(f"[Worker {id}] STARTING Read: Page {page_num}")
            data = await client.fetch_page(session, page_num, limiter)
            if data and data.patents:
                logger.info(
                    f"Worker {id} finished with Page {page_num} of patent data to write queue"
                )
                await write_queue.put(data.patents)
            else:
                logger.warning(f"[Worker {id}] Page {page_num} returned no data.")

        except Exception as e:
            logger.error(f"Error: Worker {id} crashed on page {page_num}: {e}")
        finally:
            page_queue.task_done()


async def storage_writer(write_queue: asyncio.Queue, filename: str, batch_size=5000):
    buffer = []
    while True:
        batch = await write_queue.get()
        try:
            if batch is None:
                if buffer:
                    await flush_to_storage(buffer, filename)
                break
            buffer.extend(batch)

            if len(buffer) >= batch_size:
                await flush_to_storage(buffer, filename)
                buffer.clear()
        finally:
            write_queue.task_done()


async def orchestrator(total_items, apiclient, items_per_page=1000):
    """Main handler that sets up workers for the pipeline"""
    total_pages = (total_items + items_per_page - 1) // items_per_page
    logger.info(f"Total pages: {total_pages}")

    page_queue = asyncio.Queue()
    write_queue = asyncio.Queue()
    for i in range(1, total_pages + 1):
        page_queue.put_nowait(i)
    logger.info("Page queue set up")
    limiter = RateLimiter(limit=100)
    filename = "output.jsonl"

    # Ideally you would scale workers using time for (one batch of 1000 patents)/interval
    async with ClientSession(headers=apiclient.headers) as session:
        writer_task = asyncio.create_task(
            storage_writer(write_queue, filename=filename)
        )
        fetchers = [
            asyncio.create_task(
                fetch_worker(i, page_queue, write_queue, session, apiclient, limiter)
            )
            for i in range(5)
        ]

        while not page_queue.empty():
            await asyncio.sleep(0.5)
        logger.info(
            "All pages assigned, waiting for write task to finish (with 60s timeout)..."
        )
        try:
            await asyncio.wait_for(page_queue.join(), timeout=60.0)
            logger.info("page_queue joined successfully!")
        except asyncio.TimeoutError:
            logger.error(f"STALL DETECTED: {page_queue.qsize()} items left in queue.")
            for i, f in enumerate(fetchers):
                if f.done():
                    try:
                        f.result()
                    except Exception as e:
                        logger.error(f"Fetcher {i} crashed: {e}")
        for f in fetchers:
            f.cancel()

        await write_queue.put(None)
        await write_queue.join()
        await writer_task


# This function for the sake of this excercise could:
#     - Batch insert to s3/blob
#     - Batch insert to db
#     - save to file on disk -> which ive chosen to do for the sake of the excercise
async def flush_to_storage(data, filename: str):
    if not data:
        return

    try:
        async with aiofiles.open(filename, mode="a", encoding="utf-8") as f:
            for patent in data:
                json_record = json.dumps(patent.model_dump())
                await f.write(json_record + "\n")

        logger.info(f"Successfully flushed {len(data)} records to {filename}")

    except IOError as e:
        # Disk full, permission denied, etc.
        logger.error(f"Critical I/O Error during flush: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during storage flush: {e}")
        raise
