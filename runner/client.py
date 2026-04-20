import logging
from aiohttp import ClientSession
import asyncio
from typing import Optional
from engine import RateLimiter
from models import PatentResponse, PatentRequest
import requests

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self, baseurl, token, from_date, to_date):
        self.baseurl = baseurl
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        self.validated_dates = PatentRequest(from_date=from_date, to_date=to_date)
    
    async def fetch_page(self, session: ClientSession, page: int, limiter: RateLimiter, size: int=1000, retries: int=3) -> PatentResponse:
        url = f'{self.baseurl}/patents'
        params = self.create_payload(page=page, size=size, validated_dates=self.validated_dates)
        await limiter.acquire_lock()
        # Simple retry logic in the case of 5xx errors
        for attempt in range(retries):
            try:
                async with session.post(url=url, json=params, headers=self.headers) as resp:
                    if 500 <= resp.status < 600:
                        wait = (attempt + 1) * 2
                        logger.warning(f"Server Error {resp.status}. Retry {attempt+1} in {wait}s")
                        await asyncio.sleep(wait)
                        continue

                    resp.raise_for_status()
                    data = await resp.json()
                    return PatentResponse(**data)
            except Exception as e:
                if attempt == retries - 1:
                    logger.error('Exceeded max retries')
                    raise 
                logger.error(f'Error: {e} retrying')
                await asyncio.sleep((attempt + 1) * 2)
    
    def create_payload(self, page: int, size:int, validated_dates: PatentRequest):
        return {
            'pagination': {
                'page': page,
                'page_size': size
            },
            'grant_from_date': validated_dates.from_date.isoformat(),
            'grant_to_date': validated_dates.to_date.isoformat(),
        }

    def ping_initial_metadata(self) -> Optional[PatentResponse]:
        """Sync request to get the total count before starting workers."""
        url = f'{self.baseurl}/patents'
        payload = self.create_payload(page=1, size=1, validated_dates=self.validated_dates)
        try:
            resp = requests.post(url, json=payload, headers=self.headers)
            resp.raise_for_status()
            return PatentResponse(**resp.json())
        except Exception as e:
            logger.error(f"Initial ping failed: {e}")
            return None
