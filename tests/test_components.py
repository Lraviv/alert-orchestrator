import unittest
from unittest.mock import MagicMock, AsyncMock
import asyncio

from config import Settings
from adapters.email.factory import EmailSenderFactory
from adapters.email.sender import EmailSender
from adapters.stubs import EmailSenderStub


class TestEmailSenderFactory(unittest.TestCase):
    def test_create_real_sender(self):
        settings = Settings(USE_MOCKS=False)
        sender = EmailSenderFactory.create(settings)
        self.assertIsInstance(sender, EmailSender)

    def test_create_stub_sender(self):
        settings = Settings(USE_MOCKS=True)
        sender = EmailSenderFactory.create(settings)
        self.assertIsInstance(sender, EmailSenderStub)


if __name__ == "__main__":
    unittest.main()
