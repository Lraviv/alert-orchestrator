import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
import asyncio

from services.orchestrator import AlertOrchestrator


from tests.factories import create_alert, create_recipient

from models.models import AlertStatus, FullAlert

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

        self.sample_alert = create_alert()

    async def test_process_alert_happy_path(self):
        # Setup Mocks
        recipients = [create_recipient(email="test@example.com")]
        self.mock_project_manager.resolve_recipients.return_value = FullAlert(
            alert=self.sample_alert, 
            recipients=recipients
        )
        self.mock_alert_db.persist_alert.return_value = AlertStatus.OK
        
        # Run
        await self.orchestrator.process_alert(self.sample_alert)

        # Verify Order: Resolve, then Persist, then Email
        self.mock_project_manager.resolve_recipients.assert_awaited_once_with(self.sample_alert)
        self.mock_alert_db.persist_alert.assert_awaited_once_with(self.sample_alert)
        self.mock_email_sender.send_email.assert_awaited_once()

    async def test_process_alert_deduped(self):
        # Setup Mocks
        recipients = [create_recipient(email="test@example.com")]
        self.mock_project_manager.resolve_recipients.return_value = FullAlert(
            alert=self.sample_alert, 
            recipients=recipients
        )
        self.mock_alert_db.persist_alert.return_value = AlertStatus.DEDUP

        # Run
        await self.orchestrator.process_alert(self.sample_alert)

        # Verify
        self.mock_project_manager.resolve_recipients.assert_awaited_once_with(self.sample_alert)
        self.mock_alert_db.persist_alert.assert_awaited_once_with(self.sample_alert)
        # Should NOT email if deduped (even if recipients found)
        self.mock_email_sender.send_email.assert_not_awaited()

    async def test_process_alert_no_recipients(self):
        # Setup Mocks
        self.mock_project_manager.resolve_recipients.return_value = FullAlert(
            alert=self.sample_alert, 
            recipients=[]
        )
        self.mock_alert_db.persist_alert.return_value = AlertStatus.OK

        # Run
        await self.orchestrator.process_alert(self.sample_alert)

        # Verify
        self.mock_project_manager.resolve_recipients.assert_awaited_once_with(self.sample_alert)
        # Should persist even if no recipients (assuming logic change interpretation)
        self.mock_alert_db.persist_alert.assert_awaited_once_with(self.sample_alert)
        self.mock_email_sender.send_email.assert_not_awaited()

    async def test_persist_alert_failure(self):
        # Setup Mocks - Resolve succeeds
        self.mock_project_manager.resolve_recipients.return_value = FullAlert(
            alert=self.sample_alert, 
            recipients=[create_recipient()]
        )
        # Persist fails
        self.mock_alert_db.persist_alert.side_effect = Exception("DB Down")
        
        with self.assertRaises(Exception):
            await self.orchestrator.process_alert(self.sample_alert)

    async def test_resolve_recipients_failure(self):
        # Resolve fails
        self.mock_project_manager.resolve_recipients.side_effect = Exception("PM API Down")
        
        with self.assertRaises(Exception):
            await self.orchestrator.process_alert(self.sample_alert)
        # Should not have tried to persist if resolve failed
        self.mock_alert_db.persist_alert.assert_not_awaited()

    async def test_process_alert_partial_email_failure(self):
        # Setup Mocks
        rcpt1 = create_recipient(email="user1@example.com")
        rcpt2 = create_recipient(email="user2@example.com")
        self.mock_project_manager.resolve_recipients.return_value = FullAlert(
            alert=self.sample_alert, 
            recipients=[rcpt1, rcpt2]
        )
        self.mock_alert_db.persist_alert.return_value = AlertStatus.OK
        
        # Simulate first email failing, second succeeding
        self.mock_email_sender.send_email.side_effect = [Exception("SMTP Error"), None]

        # Run
        await self.orchestrator.process_alert(self.sample_alert)

        # Verify both attempted
        self.assertEqual(self.mock_email_sender.send_email.call_count, 2)

if __name__ == "__main__":
    unittest.main()
