import logging
import smtplib
from backend.core.config import settings

logger = logging.getLogger(__name__)

def send_email_tool(to_email: str, subject: str, content: str) -> str:
    """
    Send an email via configured SMTP (Mailtrap).
    Returns "Success" or error message.
    """
    if not settings.MAIL_TRAP_USERNAME or not settings.MAIL_TRAP_PASSWORD:
        return "Error: Mailtrap credentials not set."
        
    sender = "Intelligent Content Summarization <ICS@example.com>"
    message = f"Subject: {subject}\nTo: {to_email}\nFrom: {sender}\n\n{content}"
    
    try:
        with smtplib.SMTP("sandbox.smtp.mailtrap.io", 2525) as server:
            server.starttls()
            server.login(settings.MAIL_TRAP_USERNAME, settings.MAIL_TRAP_PASSWORD)
            server.sendmail(sender, to_email, message)
        return "Success"
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return f"Error: {e}"
