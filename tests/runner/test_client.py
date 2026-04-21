from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from client import APIClient


class TestAPIClient:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient("https://api.test", "token", "2026-01-01", "2026-01-02")
        self.mock_session = MagicMock()
        self.mock_limiter = AsyncMock()
        self.mock_response = AsyncMock()

    @pytest.mark.asyncio
    async def test_fetch_page_success(self):
        self.mock_response.status = 200
        self.mock_response.json.return_value = {
            "patents": [
                {
                    "patent_number": "123",
                    "title": "Test",
                    "grant_date": "2026-01-01",
                    "abstract": "abc",
                    "claims": [],
                }
            ],
            "pagination": {
                "page": 1,
                "page_size": 1000,
                "total_items": 1,
                "total_pages": 1,
            },
        }
        self.mock_session.post.return_value.__aenter__.return_value = self.mock_response

        result = await self.client.fetch_page(self.mock_session, 1, self.mock_limiter)

        assert result.patents[0].patent_number == "123"
        self.mock_limiter.acquire_lock.assert_called_once()
        self.mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    @patch("asyncio.sleep", return_value=None)
    async def test_fetch_page_raises_on_max_retries(self, mock_sleep):
        """Test that a 500 error eventually raises an exception after retries."""
        self.mock_response.status = 500
        self.mock_session.post.return_value.__aenter__.return_value = self.mock_response

        with pytest.raises(Exception):
            await self.client.fetch_page(
                self.mock_session, 1, self.mock_limiter, retries=3
            )

        assert self.mock_session.post.call_count == 3
