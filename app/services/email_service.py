"""
Email Service for sending application emails.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional

from app.core.config import get_settings
import structlog

settings = get_settings()
logger = structlog.get_logger(__name__)

class EmailService:
    """
    Service for sending emails via SMTP.
    """

    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        sender_name: Optional[str] = "CryptoUniverse"
    ) -> bool:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: Email body in HTML format
            sender_name: Name of the sender

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not all([self.smtp_server, self.smtp_port, self.smtp_username, self.smtp_password]):
            logger.error("SMTP settings are not configured. Cannot send email.")
            return False

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{sender_name} <{self.from_email}>"
        message["To"] = to_email

        # Attach HTML content
        message.attach(MIMEText(html_content, "html"))

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.from_email, to_email, message.as_string())
            logger.info(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}", error=str(e))
            return False

# Global email service instance
email_service = EmailService()

async def get_email_service() -> EmailService:
    """
    FastAPI dependency for email service.
    """
    return email_service
