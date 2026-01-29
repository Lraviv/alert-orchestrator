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

    async def startup(self):
        """Initialize adapter connections."""
        logger.info("Starting up adapters...")
        # Start HTTP Clients
        await self.alert_db.start()
        await self.project_manager.start()
        
        # Start Email Sender (if it has a start/connect method)
        if hasattr(self.email_sender, 'connect'):
            await self.email_sender.connect()

    async def shutdown(self):
        """Close adapter connections."""
        logger.info("Shutting down adapters...")
        await self.alert_db.close()
        await self.project_manager.close()
        
        if hasattr(self.email_sender, 'close'):
            await self.email_sender.close()

    async def process_alert(self, alert: Alert):
        """
        Orchestrate the alert processing flow.
        """
        logger.info(f"Processing alert: {alert.dedup_key}")

        # 1. Resolve Recipients (FIRST)
        full_alert = await self.project_manager.resolve_recipients(alert)
        recipients = full_alert.recipients
        
        if not recipients:
            logger.warning(f"No recipients found for alert: {alert.dedup_key}")
            # Even if no recipients, we might still want to persist? 
            # User didn't specify, but usually we should persist.
            # Assuming we proceed to persist.
        
        # 2. Persist & Dedup (SECOND)
        from models.models import AlertStatus
        status = await self.alert_db.persist_alert(alert)
        
        if status == AlertStatus.DEDUP:
            logger.info(f"Alert deduped: {alert.dedup_key}")
            return

        # 3. Send Emails
        for recipient in recipients:
            try:
                await self.email_sender.send_email(recipient, alert)
            except Exception as e:
                # Log error but don't re-raise for individual recipients, assuming basic resiliency.
                logger.error(f"Failed to send email to {recipient.email}: {e}")
                pass
                
        logger.info(f"Alert processing completed: {alert.dedup_key}")
