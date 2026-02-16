import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from services.orchestrator import AlertOrchestrator
from adapters.messaging.rabbitmq import RabbitMQConsumer
from models.models import Alert
from exceptions import RetryableError, NonRetryableError

class TestErrorHandling(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_alert_db = AsyncMock()
        self.mock_project_manager = AsyncMock()
        self.mock_email_sender = AsyncMock()
        
        self.orchestrator = AlertOrchestrator(
            alert_db_client=self.mock_alert_db,
            project_manager_client=self.mock_project_manager,
            email_sender=self.mock_email_sender,
        )

    async def test_consumer_handles_success(self):
        # Mock callback
        callback = AsyncMock()
        consumer = RabbitMQConsumer(callback)
        
        # Mock message
        message = MagicMock()
        process_ctx = AsyncMock()
        process_ctx.__aenter__.return_value = message
        process_ctx.__aexit__.return_value = None
        message.process.return_value = process_ctx
        message.body = b'{"fingerprint": "123", "status": "firing", "labels": {}, "annotations": {}, "startsAt": "2023-01-01"}'
        message.ack = AsyncMock()
        message.nack = AsyncMock()
        message.reject = AsyncMock()

        # Run
        await consumer.on_message(message)

        # Verify ACK
        message.ack.assert_awaited_once()

    async def test_consumer_handles_retryable_error(self):
        # Mock callback to raise RetryableError
        callback = AsyncMock(side_effect=RetryableError("Transient"))
        consumer = RabbitMQConsumer(callback)
        
        # Mock message
        message = MagicMock()
        # Mock process() as an async context manager
        process_ctx = AsyncMock()
        process_ctx.__aenter__.return_value = message
        process_ctx.__aexit__.return_value = None
        message.process.return_value = process_ctx
        
        message.body = b'{"fingerprint": "123", "status": "firing", "labels": {}, "annotations": {}, "startsAt": "2023-01-01"}'
        
        # Async mocks for ack/nack/reject
        message.nack = AsyncMock()
        message.reject = AsyncMock()
        message.ack = AsyncMock()
        
        # Run
        await consumer.on_message(message)
        
        # Verify NACK(requeue=True)
        message.nack.assert_awaited_once_with(requeue=True)

    async def test_consumer_handles_non_retryable_error(self):
        # Mock callback to raise NonRetryableError
        callback = AsyncMock(side_effect=NonRetryableError("Fatal"))
        consumer = RabbitMQConsumer(callback)
        
        # Mock message
        message = MagicMock()
        process_ctx = AsyncMock()
        process_ctx.__aenter__.return_value = message
        process_ctx.__aexit__.return_value = None
        message.process.return_value = process_ctx

        message.body = b'{"fingerprint": "123", "status": "firing", "labels": {}, "annotations": {}, "startsAt": "2023-01-01"}'
        
        message.nack = AsyncMock()
        message.reject = AsyncMock()
        message.ack = AsyncMock()
        
        # Run
        await consumer.on_message(message)
        
        # Verify Reject(requeue=False)
        message.reject.assert_awaited_once_with(requeue=False)

if __name__ == "__main__":
    unittest.main()
