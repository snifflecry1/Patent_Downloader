# import aiohttp
from client import APIClient
import logging
import asyncio
from engine import orchestrator

BASE_URL = 'https://patent-fetcher-api.nlpatent.xyz'
TOKEN = 'demo-token-12345'

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def run():
    client = APIClient(BASE_URL, TOKEN, from_date='2026-04-01', to_date='2026-04-19')
    logger.info("Pinging API for initial metadata...")
    initial_data = client.ping_initial_metadata()
    if not initial_data:
        logger.error("Failed to retrieve data")
        return
    total_items = initial_data.pagination.total_items
    logger.info(f"Total items to download: {total_items}")

    if total_items > 0:
        try:
            asyncio.run(orchestrator(total_items, client))
            logger.info("Download process completed successfully.")
        except KeyboardInterrupt:
            logger.warning("Process interrupted by user.")
        except Exception as e:
            logger.error(f"orchestrator failed: {e}")
if __name__ == '__main__':
    run()


