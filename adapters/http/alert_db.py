from config import settings
from adapters.http.base import BaseHTTPClient
from models.models import Alert, AlertStatus

class AlertDBClient(BaseHTTPClient):
    """
    Client for interacting with the Alert DB API (Persistence & Deduplication).
    """
    def __init__(self):
        super().__init__(
            base_url=settings.ALERT_DB_API_URL,
            timeout=settings.ALERT_DB_API_TIMEOUT,
            verify_ssl=settings.SSL_VERIFY,
        )

    async def persist_alert(self, alert: Alert) -> AlertStatus:
        """
        Persist the alert and check for deduplication.
        Returns AlertStatus.OK or AlertStatus.DEDUP.
        """
        # Note: model_dump(by_alias=True) ensures 'dedup_key' is sent as 'fingerprint' if needed by DB
        json_payload = alert.model_dump(by_alias=True, mode="json")
        
        data = await self._post(
            endpoint="/alerts",
            json_payload=json_payload
        )
        status_str = data.get("status", "ok")
        
        # Map DB response to Enum
        if status_str == "dedup":
            return AlertStatus.DEDUP
        return AlertStatus.OK
