from config import settings
from adapters.http.base import BaseHTTPClient
from models.models import Alert


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

    async def persist_alert(self, alert: Alert) -> str:
        """
        Persist the alert and check for deduplication.
        Returns "ok" if new, "deduped" if already exists.
        """
        data = await self._post(
            endpoint="/alerts",
            json_payload=alert.model_dump(mode="json")
        )
        return data.get("status", "ok")
