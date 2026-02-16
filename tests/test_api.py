import unittest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
from api.health import app

class TestAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Reset state
        app.state.consumer = None
        app.state.orchestrator = None

    def test_health_connected(self):
        mock_consumer = MagicMock()
        mock_consumer.is_connected = True
        app.state.consumer = mock_consumer
        
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "OK", "rabbitmq": "connected"})

    def test_health_disconnected(self):
        mock_consumer = MagicMock()
        mock_consumer.is_connected = False
        app.state.consumer = mock_consumer
        
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "RabbitMQ Disconnected"})

    def test_health_initializing(self):
        app.state.consumer = None
        
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Initializing"})

    def test_trigger_success(self):
        # Setup a stub that has simulate_alert
        mock_consumer = MagicMock()
        mock_consumer.simulate_alert = AsyncMock()
        app.state.consumer = mock_consumer
        
        from tests.factories import create_alert_payload
        payload = create_alert_payload(
            status="firing",
            startsAt="2024-01-01T00:00:00Z"
        )
        
        response = self.client.post("/trigger", json=payload)
        self.assertEqual(response.status_code, 200)
        mock_consumer.simulate_alert.assert_awaited_once()

    def test_debug_process_success(self):
        mock_orchestrator = MagicMock()
        mock_orchestrator.process_alert = AsyncMock()
        app.state.orchestrator = mock_orchestrator
        
        from tests.factories import create_alert_payload
        payload = create_alert_payload()
        
        response = self.client.post("/debug/process", json=payload)
        self.assertEqual(response.status_code, 200)
        mock_orchestrator.process_alert.assert_awaited_once()

if __name__ == "__main__":
    unittest.main()
