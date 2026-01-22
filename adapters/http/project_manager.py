from config import settings
from adapters.http.base import BaseHTTPClient
from models.models import Alert, Recipient


class ProjectManagerClient(BaseHTTPClient):
    """
    Client for interacting with the Project Manager API (Recipient Resolution).
    """
    def __init__(self):
        super().__init__(
            base_url=settings.PROJECT_MANAGER_API_URL,
            timeout=settings.PROJECT_MANAGER_API_TIMEOUT,
            verify_ssl=settings.SSL_VERIFY,
        )

    async def resolve_recipients(self, alert: Alert) -> list[Recipient]:
        """
        Resolve recipients for the given alert.
        """
        payload = {
            "vendor": alert.vendor,
            "environment": alert.environment,
            "site": alert.site,
        }
        data = await self._post(
            endpoint="/resolve-recipients",
            json_payload=payload
        )
        return [Recipient(**r) for r in data.get("recipients", [])]
