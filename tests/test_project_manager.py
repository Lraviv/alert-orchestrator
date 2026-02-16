import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from adapters.http.project_manager import ProjectManagerClient
from tests.factories import create_alert

class TestProjectManagerClient(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = ProjectManagerClient()
        # Mock the implementation of _get because we are testing the caching wrapper
        self.client._get = AsyncMock()

    async def test_resolve_recipients_caching(self):
        # Setup
        alert = create_alert()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "recipients": [{"project_id": "p1", "project_name": "n1", "alert_groups": ["a@a.com"]}]
        }
        self.client._get.return_value = mock_resp
        
        # Run 1
        await self.client.resolve_recipients(alert)
        
        # Run 2 (Same parameters)
        await self.client.resolve_recipients(alert)
        
        # Verify _get called ONCE
        self.client._get.assert_awaited_once()

    async def test_resolve_recipients_different_params(self):
        # Setup - vary keys that are actually used (vendor, site, env)
        alert1 = create_alert(vendor="V1")
        alert2 = create_alert(vendor="V2")
        
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"recipients": []}
        self.client._get.return_value = mock_resp
        
        # Run 1
        await self.client.resolve_recipients(alert1)
        # Run 2
        await self.client.resolve_recipients(alert2)
        
        # Verify _get called TWICE
        self.assertEqual(self.client._get.call_count, 2)

if __name__ == "__main__":
    unittest.main()
