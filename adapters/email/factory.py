from typing import Union
from config import settings, Settings
from adapters.email.sender import EmailSender
from adapters.stubs import EmailSenderStub

from adapters.email.pool import SMTPConnectionPool

class EmailSenderFactory:
    """
    Factory to create EmailSender or Stub based on configuration.
    """
    @staticmethod
    def create(settings: Settings) -> Union[EmailSender, EmailSenderStub]:
        if settings.USE_MOCKS:
            return EmailSenderStub()
        
        pool = SMTPConnectionPool()
        return EmailSender(pool=pool)
