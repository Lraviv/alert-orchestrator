import aiosmtplib
import logging
from email.message import EmailMessage
from jinja2 import Environment, BaseLoader

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
        
        # Initialize Jinja2
        self.template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; }
                .alert-critical { color: red; font-weight: bold; }
                .alert-warning { color: orange; font-weight: bold; }
                .header { background-color: #f8f9fa; padding: 10px; border-bottom: 1px solid #dee2e6; }
                .content { padding: 20px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Alert Notification</h2>
            </div>
            <div class="content">
                <p><strong>Status:</strong> {{ alert.status|upper }}</p>
                <p><strong>Severity:</strong> <span class="alert-{{ alert.severity }}">{{ alert.severity|upper }}</span></p>
                <p><strong>Name:</strong> {{ alert.labels.get('alertname') }}</p>
                <p><strong>Vendor:</strong> {{ alert.vendor }}</p>
                <p><strong>Environment:</strong> {{ alert.environment }}</p>
                <p><strong>Site:</strong> {{ alert.site }}</p>
                <hr>
                <h3>Description</h3>
                <p>{{ alert.annotations.get('description', 'No description provided') }}</p>
                <br>
                <p><small>Fingerprint: {{ alert.fingerprint }}</small></p>
            </div>
        </body>
        </html>
        """
        self.jinja_env = Environment(loader=BaseLoader())
        self.template = self.jinja_env.from_string(self.template_str)

    async def send_email(self, recipient: Recipient, alert: Alert):
        """
        Send an email (HTML + Plaintext fallback) to the recipient for the given alert.
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
        
        # HTML Content
        body_html = self.template.render(alert=alert)
        message.add_alternative(body_html, subtype='html')

        try:
            await aiosmtplib.send(
                message,
                hostname=self.hostname,
                port=self.port,
                username=self.username,
                password=self.password,
                use_tls=self.use_tls,
                timeout=self.timeout,
            )
            logger.info(f"Email sent to {recipient.email} for alert {alert.fingerprint}")
        except Exception as e:
            logger.error(f"Failed to send email to {recipient.email}: {e}")
            raise
