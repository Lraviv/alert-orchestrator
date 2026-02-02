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
    """
    async def start(self):
        logger.info("[STUB] AlertDBClientStub started")

    async def close(self):
        logger.info("[STUB] AlertDBClientStub closed")

    async def persist_alert(self, alert: Alert) -> str:
        logger.info(f"[STUB] Persisting alert: {alert.fingerprint}")
        # Randomly simulate dedup
        return "ok"


class ProjectManagerClientStub(ProjectManagerClient):
    """
    Simulates the Project Manager API.
    """
    async def start(self):
        logger.info("[STUB] ProjectManagerClientStub started")

    async def close(self):
        logger.info("[STUB] ProjectManagerClientStub closed")

    async def resolve_recipients(self, alert: Alert) -> list[Recipient]:
        logger.info(f"[STUB] Resolving recipients for: {alert.fingerprint}")
        return [Recipient(project_id="p1", project_name="TestProject", alert_groups=["dev@example.com"])]


class EmailSenderStub(EmailSender):
    """
    Simulates sending an email.
    """
    def __init__(self, pool=None):
        # We don't need the pool in the stub, but we accept it to match signature
        # We call super init to satisfy linters and inheritance even if we don't use the state
        super().__init__(pool=pool)

    async def connect(self):
        logger.info("[STUB] EmailSenderStub connected")

    async def close(self):
        logger.info("[STUB] EmailSenderStub closed")

    async def send_email(self, recipients: list[Recipient], alert: Alert):
        logger.info(f"[STUB] Sending email to {len(recipients)} recipients for alert {alert.fingerprint}")


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

    async def simulate_alert(self, alert_data: dict):
        """
        Manually trigger the process callback with a dict payload.
        Useful for local testing via HTTP trigger.
        """
        try:
            alert = Alert(**alert_data)
            logger.info(f"[STUB] Simulating incoming alert: {alert.fingerprint}")
            await self.process_callback(alert)
        except Exception as e:
            logger.error(f"[STUB] Simulation failed: {e}")
            raise
