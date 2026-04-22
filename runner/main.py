import asyncio
import logging
import sys
import time
import os

from client import APIClient
from engine import orchestrator

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


BASE_URL = os.getenv("BASE_URL")
TOKEN = os.getenv("TOKEN")

def run():
    if not TOKEN:
        logger.error("API TOKEN is missing. Set it in your .env file or environment.")
        return
    if len(sys.argv) < 3:
        logger.error("Usage: docker run patent_fetcher <start_date> <end_date>")
        return
    from_date_arg = sys.argv[1]
    to_date_arg = sys.argv[2]
    client = APIClient(BASE_URL, TOKEN, from_date=from_date_arg, to_date=to_date_arg)
    logger.info("Pinging API for initial metadata...")
    initial_data = client.ping_initial_metadata()
    if not initial_data:
        logger.error("Failed to retrieve data")
        return
    total_items = initial_data.pagination.total_items
    logger.info(f"Total items to download: {total_items}")

    if total_items > 0:
        try:
            start = time.perf_counter()
            asyncio.run(orchestrator(total_items, client))
            duration = time.perf_counter() - start
            logger.info(
                f"Download process completed successfully. time took: {duration:.2f}s"
            )
        except KeyboardInterrupt:
            logger.warning("Process interrupted by user.")
        except Exception as e:
            logger.error(f"orchestrator failed: {e}")


if __name__ == "__main__":
    run()
