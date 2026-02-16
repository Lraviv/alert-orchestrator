from config import settings
from adapters.http.base import BaseHTTPClient
from models.models import Alert, AlertStatus
from exceptions import DatabaseError

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
        
        try:
            response = await self._post(
                endpoint="/alerts",
                json_payload=json_payload
            )
            data = response.json()
        except Exception as e:
            raise DatabaseError(f"Failed to persist alert in DB: {e}") from e
        status_str = data.get("status", "ok")
        
        # Map DB response to Enum
        if status_str == "dedup":
            return AlertStatus.DEDUP
        return AlertStatus.OK

    async def update_status(self, dedup_key: str, status: str):
        """
        Update the status of an alert (e.g., 'sent', 'failed').
        """
        json_payload = {"status": status, "fingerprint": dedup_key}
        try:
            # We don't care about the response body for update, just that it succeeded
            response = await self._patch(
                endpoint="/alerts",
                json_payload=json_payload
            )
            # Check for errors
            response.raise_for_status()
        except Exception as e:
            # Log but maybe don't raise? 
            # If update fails, it shouldn't fail the whole pipeline?
            # User requirement: "process alert to update email status".
            # If it fails, we should probably know.
            raise DatabaseError(f"Failed to update alert status in DB: {e}") from e
