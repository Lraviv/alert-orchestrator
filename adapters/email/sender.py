import os
import logging
import asyncio
import aiosmtplib
from email.message import EmailMessage
from jinja2 import Environment, FileSystemLoader
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings
from models.models import Alert, Recipient
from adapters.email.pool import SMTPConnectionPool
from exceptions import SMTPConnectError, SMTPDeliveryError, TemplateRenderError


logger = logging.getLogger(__name__)


class EmailSender:
    def __init__(self, pool: SMTPConnectionPool):
        self.pool = pool
        self.from_addr = settings.EMAIL_FROM
        
        # Initialize Jinja2 with FileSystemLoader
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        template_dir = os.path.join(base_dir, "templates")
        
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))

    def _prepare_email_message(self, recipient: Recipient, alert: Alert) -> EmailMessage:
        """
        Prepare the EmailMessage object with dynamic template selection.
        """
        message = EmailMessage()
        message["From"] = self.from_addr
        # Join all recipient emails from alert_groups
        to_addresses = ", ".join(recipient.alert_groups)
        
        message["To"] = to_addresses
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
        template_candidates = ["index.html", "alert.html"]
        alert_name = alert.labels.get("alertname")
        if alert_name:
            safe_name = "".join(c for c in alert_name if c.isalnum() or c in ('-', '_'))
            if safe_name:
                template_candidates.insert(0, f"{safe_name}.html")

        try:
            template = self.jinja_env.select_template(template_candidates)
            body_html = template.render(
                alert=alert,
                app_env=settings.ENVIRONMENT
            )
            message.add_alternative(body_html, subtype='html')

            # Embed images
            images_to_embed = [
                ("new_alert_banner.png", "new_alert_banner"),
                ("cloudiologo.png", "cloudiologo")
            ]
            
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            for img_filename, content_id in images_to_embed:
                img_path = os.path.join(base_dir, "templates", "images", img_filename)
                
                if os.path.exists(img_path):
                    with open(img_path, 'rb') as f:
                        img_data = f.read()
                    
                    # Attach image to the HTML part to make it multipart/related
                    payloads = message.get_payload()
                    if isinstance(payloads, list) and payloads:
                        html_part = payloads[-1]
                        
                        # Determine subtype based on extension
                        subtype = 'png' if img_filename.lower().endswith('.png') else 'jpeg'
                        
                        html_part.add_related(
                            img_data, 
                            maintype='image', 
                            subtype=subtype, 
                            cid=f'<{content_id}>',
                            filename=img_filename,
                            disposition='inline'
                        )
                else:
                    logger.warning(f"Image not found at {img_path}")

        except Exception as e:
            logger.error(f"Failed to render email template: {e}")
            pass
            
        return message

    # Proxy methods to pool for backward compatibility / Orchestrator convenience
    async def connect(self):
        await self.pool.connect()

    async def close(self):
        await self.pool.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiosmtplib.SMTPException, ConnectionError, OSError, asyncio.TimeoutError, SMTPConnectError, SMTPDeliveryError)),
    )
    async def send_email(self, recipient: Recipient, alert: Alert):
        """
        Send an email using a pooled connection.
        """
        if not recipient.alert_groups:
             logger.warning(f"No recipients for alert {alert.fingerprint}, skipping email.")
             return

        message = self._prepare_email_message(recipient, alert)
        
        try:
            async with self.pool.acquire() as client:
                await client.send_message(message)
                logger.info(f"Email sent to {len(recipient.alert_groups)} recipients for alert {alert.fingerprint}")
        except (aiosmtplib.SMTPException, ConnectionError, OSError, asyncio.TimeoutError) as e:
             logger.error(f"SMTP error sending to {len(recipient.alert_groups)} recipients: {e}")
             raise SMTPDeliveryError(f"Failed to deliver email: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            raise SMTPDeliveryError(f"Unexpected email error: {e}") from e
