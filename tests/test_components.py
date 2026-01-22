import unittest
from unittest.mock import MagicMock, AsyncMock
import asyncio

from config import Settings
from adapters.email.factory import EmailSenderFactory
from adapters.email.sender import EmailSender
from adapters.stubs import EmailSenderStub
from health import health_handler


class TestEmailSenderFactory(unittest.TestCase):
    def test_create_real_sender(self):
        settings = Settings(USE_MOCKS=False)
        sender = EmailSenderFactory.create(settings)
        self.assertIsInstance(sender, EmailSender)

    def test_create_stub_sender(self):
        settings = Settings(USE_MOCKS=True)
        sender = EmailSenderFactory.create(settings)
        self.assertIsInstance(sender, EmailSenderStub)


class TestHealthCheck(unittest.IsolatedAsyncioTestCase):
    async def test_health_connected(self):
        mock_consumer = MagicMock()
        mock_consumer.is_connected = True
        
        mock_request = MagicMock()
        mock_request.app = {"consumer": mock_consumer}
        
        response = await health_handler(mock_request)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.text, "OK")

    async def test_health_disconnected(self):
        mock_consumer = MagicMock()
        mock_consumer.is_connected = False
        
        mock_request = MagicMock()
        mock_request.app = {"consumer": mock_consumer}
        
        response = await health_handler(mock_request)
        self.assertEqual(response.status, 503)
        self.assertEqual(response.text, "RabbitMQ Disconnected")

    async def test_health_initializing(self):
        mock_request = MagicMock()
        mock_request.app = {} # No consumer key
        
        response = await health_handler(mock_request)
        self.assertEqual(response.status, 503)
        self.assertEqual(response.text, "Initializing")

if __name__ == "__main__":
    unittest.main()
