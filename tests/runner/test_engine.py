import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from engine import RateLimiter, fetch_worker, flush_to_storage, orchestrator


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_acquire_lock_spacing(self):
        """Verify that calls are spaced apart by at least the interval."""
        limit = 600
        limiter = RateLimiter(limit=limit)

        start = asyncio.get_running_loop().time()
        await limiter.acquire_lock()

        await limiter.acquire_lock()
        end = asyncio.get_running_loop().time()

        duration = end - start
        assert duration >= limiter.interval
        assert duration < limiter.interval + 0.05

    @pytest.mark.asyncio
    async def test_concurrent_burst_prevention(self):
        """Verify that multiple concurrent tasks are queued single-file."""
        limit = 600
        limiter = RateLimiter(limit=limit)

        async def call_limiter():
            await limiter.acquire_lock()
            return asyncio.get_running_loop().time()

        start = asyncio.get_running_loop().time()
        results = await asyncio.gather(call_limiter(), call_limiter(), call_limiter())

        results.sort()
        assert results[1] - results[0] >= 0.1
        assert results[2] - results[1] >= 0.1

        total_duration = results[2] - start
        assert total_duration >= 0.2


class TestEngine:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.pq = asyncio.Queue()
        self.wq = asyncio.Queue()
        self.client = MagicMock()
        self.client.fetch_page = AsyncMock()
        self.session = MagicMock()
        self.limiter = AsyncMock()
        self.mock_patent = MagicMock()
        self.mock_patent.id = "US-TEST-1"
        self.mock_patent.model_dump.return_value = {"id": "US-TEST-1"}

    @pytest.mark.asyncio
    async def test_fetch_page_success(self):
        """Test data moving into write queue"""
        await self.pq.put(1)
        self.client.fetch_page.return_value = MagicMock(patents=[self.mock_patent])
        task = asyncio.create_task(
            fetch_worker(0, self.pq, self.wq, self.session, self.client, self.limiter)
        )
        await self.pq.join()
        assert self.wq.qsize() == 1
        results = await self.wq.get()
        assert results[0].id == "US-TEST-1"
        task.cancel()

    @pytest.mark.asyncio
    async def test_fetch_page_exception(self):
        """Verify that fetch_page properly raises an exception on API failure."""
        self.client.fetch_page.side_effect = Exception("API Connection Timeout")
        with pytest.raises(Exception) as exc:
            await self.client.fetch_page(self.session, 1, self.limiter)
        assert "API Connection Timeout" in str(exc.value)

    @pytest.mark.parametrize(
        "trigger_timeout, expected_calls",
        [
            (False, 2),
            (True, 2),
        ],
    )
    @patch("engine.asyncio.wait_for")
    @patch("engine.RateLimiter.acquire_lock", new_callable=AsyncMock)
    @patch("engine.flush_to_storage", new_callable=AsyncMock)
    @patch("engine.ClientSession")
    @pytest.mark.asyncio
    async def test_orchestrator(
        self,
        mock_session,
        mock_flush,
        mock_limiter,
        mock_wait_for,
        trigger_timeout,
        expected_calls,
        caplog,
    ):
        self.client.headers = {"Authorization": "Bearer test"}
        self.client.fetch_page = AsyncMock(
            return_value=MagicMock(patents=[self.mock_patent])
        )

        if trigger_timeout:
            mock_wait_for.side_effect = asyncio.TimeoutError()

        await orchestrator(total_items=2, apiclient=self.client, items_per_page=1)
        if trigger_timeout:
            assert "STALL DETECTED" in caplog.text
            assert any(record.levelname == "ERROR" for record in caplog.records)

        assert self.client.fetch_page.call_count == expected_calls
        assert mock_flush.called

        flushed_list = mock_flush.call_args[0][0]
        assert flushed_list[0].id == "US-TEST-1"

    @pytest.mark.asyncio
    async def test_flush_to_storage_success(self):
        """Verify successfully flushes to test file"""
        data = [self.mock_patent]
        filename = "test_output.jsonl"
        mock_file_handle = MagicMock()
        mock_file_handle.write = AsyncMock()
        mock_aio_open = MagicMock()
        mock_aio_open.return_value.__aenter__ = AsyncMock(return_value=mock_file_handle)
        mock_aio_open.return_value.__aexit__ = AsyncMock()
        with patch("engine.aiofiles.open", mock_aio_open):
            await flush_to_storage(data, filename)
        mock_aio_open.assert_called_once_with(filename, mode="a", encoding="utf-8")

        expected_json = json.dumps({"id": "US-TEST-1"}) + "\n"
        mock_file_handle.write.assert_called_once_with(expected_json)

    @pytest.mark.asyncio
    async def test_flush_to_storage_io_error(self):
        with patch("aiofiles.open", side_effect=IOError("Disk Full")):
            with pytest.raises(IOError, match="Disk Full"):
                await flush_to_storage([self.mock_patent], "fail.jsonl")
