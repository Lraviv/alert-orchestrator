import asyncio
import json
import logging
from typing import Callable, Awaitable, Optional

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from config import settings
from models.models import Alert
from exceptions import RetryableError, NonRetryableError

logger = logging.getLogger(__name__)


class RabbitMQConsumer:
    def __init__(self, process_alert_callback: Callable[[Alert], Awaitable[None]]):
        self.url = settings.RABBITMQ_URL
        self.queue_name = settings.RABBITMQ_QUEUE_NAME
        self.prefetch_count = settings.RABBITMQ_PREFETCH_COUNT
        self.process_callback = process_alert_callback
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None

    @property
    def is_connected(self) -> bool:
        return self.connection is not None and not self.connection.is_closed

    async def connect(self):
        try:
            self.connection = await aio_pika.connect_robust(
                self.url,
                client_properties={"connection_name": "alert-orchestrator"}
            )
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=self.prefetch_count)
            
            # Declare queue (durable)
            queue = await self.channel.declare_queue(
                self.queue_name,
                durable=True,
                arguments={"x-max-priority": 10}  # Support priority
            )
            
            await queue.consume(self.on_message)
            logger.info(f"RabbitMQ connected and consuming from {self.queue_name}")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def on_message(self, message: AbstractIncomingMessage):
        async with message.process(ignore_processed=True):
            try:
                body = message.body.decode()
                logger.debug(f"Message received: {body}")
                
                try:
                    alert_data = json.loads(body)
                    alert = Alert(**alert_data)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Invalid message format: {e}. Body: {body}")
                    await message.reject(requeue=False)
                    return

                await self.process_callback(alert)
                logger.info(f"Message processed successfully: {alert.fingerprint}")
                await message.ack()
                
            except RetryableError as e:
                logger.warning(f"Retryable error processing alert: {e}")
                # Requeue message to be retried
                await message.nack(requeue=True)
            except NonRetryableError as e:
                logger.error(f"Non-retryable error processing alert: {e}")
                # Dead letter or discard
                await message.reject(requeue=False)
            except Exception as e:
                logger.error(f"Unexpected error processing message: {e}")
                # Re-raise to trigger nack (default behavior of aio_pika process context manager depending on version/handling)
                # But we are in a Manual loop logic here.
                # 'message.process' context manager automatically acks if no exception, and nacks if exception is raised (if ignore_processed=False).
                # We passed ignore_processed=True, so we are manually responsible?
                # Docs say: `async with message.process():`
                # If ignore_processed=True, it DOES NOT auto ack/nack?
                # Actually, `message.process()` does catch exceptions and NACKs if ignore_processed=False (default).
                # Code uses `ignore_processed=True`. Why?
                # "When ignore_processed=True you must process message manually (ack, reject, nack)"
                # Wait, looking at line 51: `async with message.process(ignore_processed=True):`
                # If so, existing code `raise e` at line 70 would crash the consumer loop unless `message.process` catches it?
                # aio-pika's `process` context manager (if default) catches exception and nacks.
                # If `ignore_processed=True`, it probably does NOTHING.
                # So if loop logic raises, valid.
                
                # I should handle it explicitly to be safe.
                # Default safety: NACK (requeue) for transient.
                await message.nack(requeue=True)

    async def close(self):
        if self.connection:
            await self.connection.close()
