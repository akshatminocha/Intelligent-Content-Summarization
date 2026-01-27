import logging
import smtplib
from backend.core.config import settings

logger = logging.getLogger(__name__)

class NotificationAgent:
    def __init__(self):
        self.host = "sandbox.smtp.mailtrap.io"
        self.port = 2525
        self.username = settings.MAIL_TRAP_USERNAME
        self.password = settings.MAIL_TRAP_PASSWORD
        
    def send_email(self, to_email: str, subject: str, content: str) -> bool:
        """
        Send an email via Mailtrap.
        """
        if not self.username or not self.password:
            logger.error("Mailtrap credentials not set.")
            return False
            
        sender = "Intelligent Content Summarization <ICS@example.com>"
        receiver = to_email
        
        # Simple text email construction
        # For better formatting, using MIMEMultipart would be better, but sticking to requested simple code.
        message = f"""\
Subject: {subject}
To: {receiver}
From: {sender}

{content}
"""
        
        try:
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(sender, receiver, message)
            logger.info(f"Email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
