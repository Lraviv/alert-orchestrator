import logging

from adapters.email.sender import EmailSender
from adapters.http.alert_db import AlertDBClient
from adapters.http.project_manager import ProjectManagerClient
from models.models import Alert

logger = logging.getLogger(__name__)


class AlertOrchestrator:
    def __init__(
        self,
        alert_db_client: AlertDBClient,
        project_manager_client: ProjectManagerClient,
        email_sender: EmailSender,
    ):
        self.alert_db = alert_db_client
        self.project_manager = project_manager_client
        self.email_sender = email_sender

    async def process_alert(self, alert: Alert):
        """
        Orchestrate the alert processing flow.
        """
        logger.info(f"Processing alert: {alert.fingerprint}")

        # 1. Persist & Dedup
        status = await self.alert_db.persist_alert(alert)
        if status == "deduped":
            logger.info(f"Alert deduped: {alert.fingerprint}")
            return

        # 2. Resolve Recipients
        recipients = await self.project_manager.resolve_recipients(alert)
        if not recipients:
            logger.warning(f"No recipients found for alert: {alert.fingerprint}")
            return

        # 3. Send Emails
        for recipient in recipients:
            try:
                await self.email_sender.send_email(recipient, alert)
            except Exception as e:
                # Log error but don't re-raise for individual recipients, assuming basic resiliency.
                # However, previous logic was to log and pass.
                logger.error(f"Failed to send email to {recipient.email}: {e}")
                pass
                
        logger.info(f"Alert processing completed: {alert.fingerprint}")
