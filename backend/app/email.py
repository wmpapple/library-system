"""Email sending utility."""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from . import config

logger = logging.getLogger(__name__)


def send_email(subject: str, body: str, email_to: str | None = None):
    """Sends an email using the configured SMTP settings."""
    # If no specific recipient is provided, fall back to the admin email.
    recipient = email_to or config.ADMIN_EMAIL

    if not config.EMAIL_ENABLED:
        logger.info("Email notifications are disabled. Skipping sending.")
        return

    if not recipient:
        logger.warning("No recipient email address provided. Skipping sending.")
        return

    # Ensure SMTP settings are minimally configured
    if not all([config.SMTP_HOST, config.SMTP_PORT, config.SMTP_USER]):
        logger.error("SMTP settings are incomplete. Cannot send email.")
        return

    message = MIMEMultipart()
    message["From"] = config.SMTP_USER
    message["To"] = recipient
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))

    server = None
    try:
        if config.SMTP_SSL:
            # Use SMTP_SSL for connections that are encrypted from the start (e.g., port 465)
            server = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT)
        else:
            # Use standard SMTP for connections that start plain and may be upgraded
            server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT)
            if config.SMTP_TLS:
                server.starttls()

        if config.SMTP_USER and config.SMTP_PASSWORD:
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        
        server.sendmail(config.SMTP_USER, recipient, message.as_string())
        logger.info(f"Email sent successfully to {recipient}")

    except smtplib.SMTPException as e:
        logger.error(f"Failed to send email via SMTP to {recipient}: {e}", exc_info=True)
    except OSError as e:
        logger.error(f"A network error occurred while sending email to {recipient}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending email to {recipient}: {e}", exc_info=True)
    finally:
        if server:
            try:
                server.quit()
            except smtplib.SMTPException:
                pass # Ignore errors on quit
