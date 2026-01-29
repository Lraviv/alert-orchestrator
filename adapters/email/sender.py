import os
import logging
import aiosmtplib
from email.message import EmailMessage
from jinja2 import Environment, FileSystemLoader
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings
from models.models import Alert, Recipient

logger = logging.getLogger(__name__)


class EmailSender:
    def __init__(self):
        self.hostname = settings.SMTP_HOSTNAME
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.use_tls = settings.SMTP_USE_TLS
        self.timeout = settings.SMTP_TIMEOUT
        self.from_addr = settings.EMAIL_FROM
        
        # Initialize Jinja2 with FileSystemLoader
        # Assuming templates are in "templates" dir at project root
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        template_dir = os.path.join(base_dir, "templates")
        
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
        # Template loading is now dynamic in _prepare_email_message

    def _prepare_email_message(self, recipient: Recipient, alert: Alert) -> EmailMessage:
        """
        Prepare the EmailMessage object with dynamic template selection.
        """
        message = EmailMessage()
        message["From"] = self.from_addr
        message["To"] = recipient.email
        message["Subject"] = f"Alert: {alert.labels.get('alertname', 'Unknown Alert')} - {alert.severity.upper()}"
        
        # Plain text fallback
        body_text = f"""
        Alert Details:
        --------------
        Name: {alert.labels.get('alertname')}
        Severity: {alert.severity}
        Status: {alert.status}
        Environment: {alert.environment}
        Site: {alert.site}
        Description: {alert.annotations.get('description')}
        """
        message.set_content(body_text)
        
        # Dynamic Template Selection
        # 1. Try "AlertName.html"
        # 2. Fallback to "alert.html"
        template_candidates = ["alert.html"]
        alert_name = alert.labels.get("alertname")
        if alert_name:
            # Sanitize simple filename safety (basic)
            safe_name = "".join(c for c in alert_name if c.isalnum() or c in ('-', '_'))
            if safe_name:
                template_candidates.insert(0, f"{safe_name}.html")

        try:
            template = self.jinja_env.select_template(template_candidates)
            body_html = template.render(alert=alert)
            message.add_alternative(body_html, subtype='html')
        except Exception as e:
            logger.error(f"Failed to render email template: {e}")
            # Fallback to just plain text if rendering fails? OR re-raise?
            # For now, let's keep the plain text part and maybe log.
            # But add_alternative failing prevents HTML.
            pass
            
        return message

    async def connect(self):
        """Initialize the persistent SMTP client."""
        # Note: aiosmtplib.SMTP acts as a context manager or explicit connect.
        # We will usage explicit connect.
        self.smtp_client = aiosmtplib.SMTP(
            hostname=self.hostname,
            port=self.port,
            use_tls=self.use_tls,
            timeout=self.timeout
        )
        await self.smtp_client.connect()
        if self.username and self.password:
            await self.smtp_client.login(self.username, self.password)

    async def close(self):
        """Close the persistent SMTP client."""
        if hasattr(self, 'smtp_client') and self.smtp_client:
            self.smtp_client.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiosmtplib.SMTPException, ConnectionError, OSError)),
    )
    async def send_email(self, recipient: Recipient, alert: Alert):
        """
        Send an email (HTML + Plaintext fallback) to the recipient for the given alert.
        """
        try:
            message = self._prepare_email_message(recipient, alert)
            
            # Lazy connect if not connected
            if not hasattr(self, 'smtp_client') or not self.smtp_client or not self.smtp_client.is_connected:
                 await self.connect()

            await self.smtp_client.send_message(message)
            logger.info(f"Email sent to {recipient.email} for alert {alert.fingerprint}")
        except Exception as e:
            # Force close on error to ensure reconnection next time
            if hasattr(self, 'smtp_client') and self.smtp_client:
                 self.smtp_client.close()
            logger.error(f"Failed to send email to {recipient.email}: {e}")
            raise
