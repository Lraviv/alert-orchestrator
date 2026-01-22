import logging
import asyncio
from typing import Callable, Awaitable

from adapters.http.alert_db import AlertDBClient
from adapters.http.project_manager import ProjectManagerClient
from adapters.email.sender import EmailSender
from adapters.messaging.rabbitmq import RabbitMQConsumer
from models.models import Alert, Recipient

logger = logging.getLogger(__name__)

"""
STUBS
-----
Stubs are simple, in-memory implementations of the adapter interfaces.
They are used for:
1. Local Development: Running the service without needing RabbitMQ, REST APIs, or SMTP servers.
2. Wiring Verification: Ensuring that the dependency injection logic works correctly.

Usage: Set USE_MOCKS=True in config.py or environment variables.
"""


class AlertDBClientStub(AlertDBClient):
    """
    Simulates the Alert Database.
    Always returns 'ok' by default, or you can modify it to simulate dedup logic.
    """
    async def persist_alert(self, alert: Alert) -> str:
        logger.info(f"[STUB] Persisting alert: {alert.fingerprint}")
        # Randomly simulate dedup
        return "ok"


class ProjectManagerClientStub(ProjectManagerClient):
    """
    Simulates the Project Manager API.
    Always returns a hardcoded recipient list.
    """
    async def resolve_recipients(self, alert: Alert) -> list[Recipient]:
        logger.info(f"[STUB] Resolving recipients for: {alert.dedup_key}")
        return [Recipient(email="dev@example.com", group_name="DevOps")]


class EmailSenderStub(EmailSender):
    """
    Simulates sending an email.
    Instead of connecting to SMTP, it just logs the email attempt.
    """
    async def send_email(self, recipient: Recipient, alert: Alert):
        logger.info(f"[STUB] Sending email to {recipient.email} for alert {alert.dedup_key}")


class RabbitMQConsumerStub(RabbitMQConsumer):
    """
    Simulates a RabbitMQ Consumer.
    It doesn't connect to any broker. Use this to verify startup logic.
    To simulate a message, you would need to call process_callback manually.
    """
    def __init__(self, process_alert_callback: Callable[[Alert], Awaitable[None]]):
        self.process_callback = process_alert_callback
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self):
        logger.info("[STUB] RabbitMQ Stub connected (No real connection)")
        self._connected = True
        pass

    async def close(self):
        logger.info("[STUB] RabbitMQ Stub closed")
        self._connected = False
