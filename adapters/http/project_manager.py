from config import settings
from adapters.http.base import BaseHTTPClient
from httpx import Response
from models.models import Alert, Recipient, FullAlert
from exceptions import ProjectResolutionRetryableError, ProjectResolutionNonRetryableError
from async_lru import alru_cache
from typing import Any

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

    @alru_cache(maxsize=128, ttl=60)
    async def _resolve_cached(self, vendor_id: str, environment: str, site: str) -> Response:
        """
        Cached internal helper.
        """
        payload = {
            "vendor": vendor,
            "environment": environment,
            "site": site,
        }
        response = await self._get(
            endpoint=f"/resolve-recipients/{vendor_id}/alerts_groups",
            params=payload
        )
        return response

    async def resolve_recipients(self, alert: Alert) -> FullAlert:
        """
        Resolve recipients for the given alert and return a FullAlert.
        """
        try:
            data = await self._resolve_cached(
                vendor=alert.vendor,
                environment=alert.environment,
                site=alert.site
            )
        except Exception as e:
             status = 500
             if isinstance(e, httpx.HTTPStatusError):
                 status = e.response.status_code
                 
             if 400 <= status < 500:
                 raise ProjectResolutionNonRetryableError(f"Failed to resolve recipients (4xx): {e}") from e
             raise ProjectResolutionRetryableError(f"Failed to resolve recipients: {e}") from e
        recipients_data = data.get("recipients", [])
        
        # Merge all alert_groups from all recipients found
        merged_groups = []
        project_id = "unknown"
        project_name = "unknown"
        
        if recipients_data:
            # Take identity from first recipient
            project_id = recipients_data[0].get("project_id", "unknown")
            project_name = recipients_data[0].get("project_name", "unknown")
            
            for r in recipients_data:
                groups = r.get("alert_groups", [])
                if groups:
                    merged_groups.extend(groups)
        
        # De-dup emails
        merged_groups = list(set(merged_groups))

        return FullAlert(
            **alert.model_dump(),
            project_id=project_id,
            project_name=project_name,
            alert_groups=merged_groups
        )
