import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import httpx
from adapters.http.base import BaseHTTPClient

class TestBaseHTTPClient(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = BaseHTTPClient(base_url="http://test", timeout=1.0)
        self.mock_httpx = AsyncMock()
        self.mock_httpx.is_closed = False
        self.client.client = self.mock_httpx
        
        # Patch sleep to avoid waiting during tests
        patcher = patch("asyncio.sleep", new_callable=AsyncMock)
        self.mock_sleep = patcher.start()
        self.addCleanup(patcher.stop)

    async def test_post_success(self):
        # Setup
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"ok": True}
        self.mock_httpx.post.return_value = resp
        
        # Run
        result = await self.client._post("endpoint", {})
        
        # Verify
        self.assertEqual(result.json(), {"ok": True})
        self.assertEqual(self.mock_httpx.post.call_count, 1)

    async def test_post_retry_on_connection_error(self):
        # Fail twice with RequestError, then succeed
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"ok": True}
        
        self.mock_httpx.post.side_effect = [
            httpx.RequestError("ConnErr"), 
            httpx.RequestError("ConnErr"), 
            resp
        ]
        
        # Run
        result = await self.client._post("endpoint", {})
        
        # Verify
        self.assertEqual(result.json(), {"ok": True})
        self.assertEqual(self.mock_httpx.post.call_count, 3)

    async def test_post_retry_on_500(self):
        # Fail twice with 500, then succeed
        resp_500 = MagicMock()
        resp_500.status_code = 500
        error_500 = httpx.HTTPStatusError("500", request=MagicMock(), response=resp_500)
        
        resp_ok = MagicMock()
        resp_ok.status_code = 200
        resp_ok.json.return_value = {"ok": True}
        
        # Post mock
        # Note: client.post returns response, which we explicitly raise_for_status() on.
        # But wait, BaseHTTPClient logic calls `response.raise_for_status()`.
        # So mocks must return a response that raises or doesn't.
        
        # Fix: Mock the response object returned by client.post
        mock_resp_500 = MagicMock()
        mock_resp_500.raise_for_status.side_effect = error_500
        mock_resp_500.json.return_value = {}

        mock_resp_ok = MagicMock()
        mock_resp_ok.raise_for_status.return_value = None
        mock_resp_ok.json.return_value = {"ok": True}
        
        self.mock_httpx.post.side_effect = [mock_resp_500, mock_resp_500, mock_resp_ok]
        
        # Run
        result = await self.client._post("endpoint", {})
        
        # Verify
        self.assertEqual(result.json(), {"ok": True})
        self.assertEqual(self.mock_httpx.post.call_count, 3)

    async def test_post_no_retry_on_400(self):
        # Fail with 400
        resp_400 = MagicMock()
        resp_400.status_code = 400
        error_400 = httpx.HTTPStatusError("400", request=MagicMock(), response=resp_400)
        
        mock_resp_400 = MagicMock()
        mock_resp_400.raise_for_status.side_effect = error_400
        
        self.mock_httpx.post.side_effect = [mock_resp_400]
        
        # Run
        with self.assertRaises(httpx.HTTPStatusError):
            await self.client._post("endpoint", {})
            
        # Verify call count 1 (no retry)
        self.assertEqual(self.mock_httpx.post.call_count, 1)

    async def test_post_retry_on_429(self):
        # Fail twice with 429, then succeed
        resp_429 = MagicMock()
        resp_429.status_code = 429
        error_429 = httpx.HTTPStatusError("429", request=MagicMock(), response=resp_429)
        
        mock_resp_429 = MagicMock()
        mock_resp_429.raise_for_status.side_effect = error_429
        
        mock_resp_ok = MagicMock()
        mock_resp_ok.raise_for_status.return_value = None
        mock_resp_ok.json.return_value = {"ok": True}
        
        self.mock_httpx.post.side_effect = [mock_resp_429, mock_resp_429, mock_resp_ok]
        
        # Run
        result = await self.client._post("endpoint", {})
        
        # Verify
        self.assertEqual(result.json(), {"ok": True})
        self.assertEqual(self.mock_httpx.post.call_count, 3)

    async def test_get_success(self):
        # Setup
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"data": "yes"}
        self.mock_httpx.get.return_value = resp
        
        # Run
        result = await self.client._get("endpoint", {"q": 1})
        
        # Verify
        self.assertEqual(result.json(), {"data": "yes"})
        self.mock_httpx.get.assert_awaited_once()

if __name__ == "__main__":
    unittest.main()
