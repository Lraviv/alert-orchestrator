from config import settings
from adapters.http.base import BaseHTTPClient
from models.models import Alert, Recipient, FullAlert


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

    async def resolve_recipients(self, alert: Alert) -> FullAlert:
        """
        Resolve recipients for the given alert and return a FullAlert.
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
