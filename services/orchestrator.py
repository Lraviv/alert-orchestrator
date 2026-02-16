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
        # Note: full_alert is (Alert + Recipient)
        
        if not full_alert.alert_groups:
            logger.warning(f"No recipients found for alert: {full_alert.dedup_key}")
            # Even if no recipients, we might still want to persist? 
            # User didn't specify, but usually we should persist.
            # Assuming we proceed to persist.
        
        # 2. Persist & Dedup (SECOND)
        from models.models import AlertStatus
        # We persist the original alert part, or full_alert? 
        # Persistence expects Alert. FullAlert inherits Alert, so it works.
        status = await self.alert_db.persist_alert(full_alert)
        
        if status == AlertStatus.DEDUP:
            logger.info(f"Alert deduped: {full_alert.dedup_key}")
            return

        # 3. Send Emails
        if full_alert.alert_groups:
            try:
                # full_alert serves as both Recipient (1st arg) and Alert (2nd arg)
                await self.email_sender.send_email(full_alert, full_alert)
            except Exception as e:
                logger.error(f"Failed to send email for {alert.dedup_key}: {e}")
                # Update Status: FAILED
                try:
                    await self.alert_db.update_status(alert.dedup_key, AlertStatus.FAILED)
                except Exception as db_e:
                    logger.error(f"Failed to update failures status for {alert.dedup_key}: {db_e}")
                # Re-raise the original error (to trigger Retry or DLQ) so we don't lose the alert
                raise

            # 4. Update Status: SENT
            # We do this OUTSIDE the email try-except block.
            # If this fails, we catch and log it, but DO NOT raise, 
            # because the email was already sent successfully.
            # We do NOT want to NACK and retry sending the email again.
            try:
                await self.alert_db.update_status(alert.dedup_key, AlertStatus.SENT)
            except Exception as e:
                 logger.error(f"Failed to update status to SENT for {alert.dedup_key}: {e}")
                
        logger.info(f"Alert processing completed: {alert.dedup_key}")
