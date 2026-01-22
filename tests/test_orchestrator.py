import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
import asyncio

from models.models import Alert, Recipient
from services.orchestrator import AlertOrchestrator


class TestAlertOrchestrator(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_alert_db = AsyncMock()
        self.mock_project_manager = AsyncMock()
        self.mock_email_sender = AsyncMock()
        
        self.orchestrator = AlertOrchestrator(
            alert_db_client=self.mock_alert_db,
            project_manager_client=self.mock_project_manager,
            email_sender=self.mock_email_sender,
        )

        self.sample_alert = Alert(
            status="firing",
            labels={"alertname": "TestAlert", "severity": "critical", "vendor": "TestVendor"},
            annotations={"description": "Something failed"},
            startsAt=datetime.now(),
            fingerprint="test-fp",
        )

    async def test_process_alert_happy_path(self):
        # Setup Mocks
        self.mock_alert_db.persist_alert.return_value = "ok"
        self.mock_project_manager.resolve_recipients.return_value = [
            Recipient(email="test@example.com")
        ]

        # Run
        await self.orchestrator.process_alert(self.sample_alert)

        # Verify
        self.mock_alert_db.persist_alert.assert_awaited_once_with(self.sample_alert)
        self.mock_project_manager.resolve_recipients.assert_awaited_once_with(self.sample_alert)
        self.mock_email_sender.send_email.assert_awaited_once()

    async def test_process_alert_deduped(self):
        # Setup Mocks
        self.mock_alert_db.persist_alert.return_value = "deduped"

        # Run
        await self.orchestrator.process_alert(self.sample_alert)

        # Verify
        self.mock_alert_db.persist_alert.assert_awaited_once_with(self.sample_alert)
        self.mock_project_manager.resolve_recipients.assert_not_awaited()
        self.mock_email_sender.send_email.assert_not_awaited()

    async def test_process_alert_no_recipients(self):
        # Setup Mocks
        self.mock_alert_db.persist_alert.return_value = "ok"
        self.mock_project_manager.resolve_recipients.return_value = []

        # Run
        await self.orchestrator.process_alert(self.sample_alert)

        # Verify
        self.mock_alert_db.persist_alert.assert_awaited_once_with(self.sample_alert)
        self.mock_project_manager.resolve_recipients.assert_awaited_once_with(self.sample_alert)
        self.mock_email_sender.send_email.assert_not_awaited()

    async def test_persist_alert_failure(self):
        # Verify exception bubbles up (so RabbitMQ nacks)
        self.mock_alert_db.persist_alert.side_effect = Exception("DB Down")
        
        with self.assertRaises(Exception):
            await self.orchestrator.process_alert(self.sample_alert)

    async def test_resolve_recipients_failure(self):
        # Verify exception bubbles up
        self.mock_alert_db.persist_alert.return_value = "ok"
        self.mock_project_manager.resolve_recipients.side_effect = Exception("PM API Down")
        
        with self.assertRaises(Exception):
            await self.orchestrator.process_alert(self.sample_alert)

    async def test_process_alert_partial_email_failure(self):
        # Setup Mocks
        self.mock_alert_db.persist_alert.return_value = "ok"
        rcpt1 = Recipient(email="user1@example.com")
        rcpt2 = Recipient(email="user2@example.com")
        self.mock_project_manager.resolve_recipients.return_value = [rcpt1, rcpt2]
        
        # Simulate first email failing, second succeeding
        self.mock_email_sender.send_email.side_effect = [Exception("SMTP Error"), None]

        # Run (should NOT raise, as orchestrator catches email errors)
        await self.orchestrator.process_alert(self.sample_alert)

        # Verify both attempted
        import unittest.mock
        # Check call args list or count
        self.assertEqual(self.mock_email_sender.send_email.call_count, 2)

if __name__ == "__main__":
    unittest.main()
