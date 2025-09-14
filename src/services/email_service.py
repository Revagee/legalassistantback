import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


class EmailConfig:
    """Email configuration from environment variables."""

    SMTP_HOST = os.getenv("MAILGUN_SMTP_SERVER", "smtp.mailgun.org")
    SMTP_PORT = int(os.getenv("MAILGUN_SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("MAILGUN_SMTP_LOGIN", "")
    SMTP_PASSWORD = os.getenv("MAILGUN_SMTP_PASSWORD", "")
    FROM_EMAIL = "noreply@watchnext.ai"
    FROM_NAME = "WatchNext"

    API_BASE_URL = os.getenv("API_BASE_URL", "https://api.watchnext.ai")
    WEB_BASE_URL = os.getenv("WEB_BASE_URL", "https://watchnext.ai")
    USE_MOCK_EMAIL = os.getenv("USE_MOCK_EMAIL", "true").lower() == "true"


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        self.config = EmailConfig()

    async def send_email(self, to_email: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
        """Send an email."""
        if self.config.USE_MOCK_EMAIL:
            return await self._send_mock_email(to_email, subject, html_body)
        else:
            return await self._send_smtp_email(to_email, subject, html_body, text_body)

    async def _send_mock_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """Mock email sending for development."""
        logger.info("🔔 MOCK EMAIL SENT 📧")
        logger.info(f"To: {to_email}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Body: {html_body}")
        logger.info("=" * 50)
        return True

    async def _send_smtp_email(
        self, to_email: str, subject: str, html_body: str, text_body: Optional[str] = None
    ) -> bool:
        """Send email via SMTP."""
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.config.FROM_NAME} <{self.config.FROM_EMAIL}>"
        msg["To"] = to_email

        # Add text part if provided
        if text_body:
            text_part = MIMEText(text_body, "plain")
            msg.attach(text_part)

        # Add HTML part
        html_part = MIMEText(html_body, "html")
        msg.attach(html_part)

        # Send email
        with smtplib.SMTP(self.config.SMTP_HOST, self.config.SMTP_PORT) as server:
            server.starttls()
            server.login(self.config.SMTP_USERNAME, self.config.SMTP_PASSWORD)
            server.send_message(msg)

        return True

    async def send_verification_email(self, to_email: str, verification_token: str) -> bool:
        """Send email verification email."""
        verification_url = f"{self.config.WEB_BASE_URL}/verify-email?token={verification_token}"

        subject = "Verify your WatchNext account"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Verify Your Email</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #6366f1;">WatchNext</h1>
                </div>

                <h2>Verify Your Email Address</h2>

                <p>Thank you for creating a WatchNext account! To complete your registration, please verify your email address by clicking the button below:</p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}"
                       style="background-color: #6366f1; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Verify Email Address
                    </a>
                </div>

                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #6366f1;">{verification_url}</p>

                <p><strong>This link will expire in 24 hours.</strong></p>
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">

                <p style="font-size: 14px; color: #666;">
                    If you didn't create a WatchNext account, you can safely ignore this email.
                </p>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Verify Your WatchNext Account

        Thank you for creating a WatchNext account! To complete your registration, please verify your email address by visiting this link:

        {verification_url}

        This link will expire in 24 hours.

        If you didn't create a WatchNext account, you can safely ignore this email.
        """

        return await self.send_email(to_email, subject, html_body, text_body)

    async def send_password_reset_email(self, to_email: str, reset_token: str) -> bool:
        """Send password reset email."""
        reset_url = f"{self.config.WEB_BASE_URL}/reset-password?token={reset_token}"

        subject = "Reset your WatchNext password"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Reset Your Password</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #6366f1;">WatchNext</h1>
                </div>

                <h2>Reset Your Password</h2>

                <p>We received a request to reset your WatchNext account password. Click the button below to create a new password:</p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}"
                       style="background-color: #6366f1; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Reset Password
                    </a>
                </div>

                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #6366f1;">{reset_url}</p>

                <p><strong>This link will expire in 24 hours.</strong></p>

                <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">

                <p style="font-size: 14px; color: #666;">
                    If you didn't request a password reset, you can safely ignore this email. Your password will not be changed.
                </p>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Reset Your WatchNext Password

        We received a request to reset your WatchNext account password. Visit this link to create a new password:

        {reset_url}

        This link will expire in 24 hours.

        If you didn't request a password reset, you can safely ignore this email. Your password will not be changed.
        """.strip()

        return await self.send_email(to_email, subject, html_body, text_body)
