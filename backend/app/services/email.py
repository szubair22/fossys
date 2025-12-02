"""
Email notification service for OrgSuite.

This module provides a pluggable email service that can be configured
to use different providers (SMTP, SendGrid, SES, etc.).

For development/testing, emails are logged to console/file instead of sent.
"""
import logging
from typing import Optional
from datetime import datetime
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service for sending notifications.

    In development mode, emails are logged to a file.
    In production, this can be extended to use SMTP, SendGrid, AWS SES, etc.
    """

    def __init__(self):
        self.from_email = getattr(settings, 'FROM_EMAIL', 'noreply@orgmeet.com')
        self.from_name = getattr(settings, 'FROM_NAME', 'OrgMeet')
        self.site_url = getattr(settings, 'SITE_URL', 'http://localhost:3000')
        self.debug = getattr(settings, 'DEBUG', True)
        self.email_log_path = Path('/tmp/orgmeet_emails.log')

    def _log_email(self, to: str, subject: str, body: str, html: Optional[str] = None):
        """Log email to file for development/testing."""
        timestamp = datetime.now().isoformat()
        log_entry = f"""
================================================================================
EMAIL SENT: {timestamp}
================================================================================
TO: {to}
FROM: {self.from_name} <{self.from_email}>
SUBJECT: {subject}
--------------------------------------------------------------------------------
BODY:
{body}
--------------------------------------------------------------------------------
"""
        if html:
            log_entry += f"""
HTML:
{html}
--------------------------------------------------------------------------------
"""

        # Log to file
        with open(self.email_log_path, 'a') as f:
            f.write(log_entry)

        # Also log to console
        logger.info(f"Email logged: to={to}, subject={subject}")
        if self.debug:
            print(f"\n[EMAIL] To: {to} | Subject: {subject}")
            print(f"[EMAIL] Body: {body[:200]}...")

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: Optional[str] = None
    ) -> bool:
        """
        Send an email.

        Args:
            to: Recipient email address
            subject: Email subject line
            body: Plain text body
            html: Optional HTML body

        Returns:
            True if email was sent/logged successfully
        """
        try:
            if self.debug:
                # In development, just log the email
                self._log_email(to, subject, body, html)
                return True

            # TODO: In production, implement actual email sending here
            # Options:
            # - SMTP via smtplib
            # - SendGrid API
            # - AWS SES
            # - Mailgun
            # For now, still log even in "production" mode
            self._log_email(to, subject, body, html)
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            return False

    async def send_invitation_email(
        self,
        to: str,
        organization_name: str,
        inviter_name: str,
        role: str,
        invite_token: str,
        message: Optional[str] = None
    ) -> bool:
        """
        Send an organization invitation email.

        Args:
            to: Recipient email address
            organization_name: Name of the organization
            inviter_name: Name of the person who sent the invitation
            role: Role being offered (admin, member, viewer)
            invite_token: Secure token for accepting the invite
            message: Optional personal message from inviter
        """
        invite_url = f"{self.site_url}/pages/register.html?invite={invite_token}"

        subject = f"You're invited to join {organization_name} on OrgMeet"

        body = f"""Hello,

{inviter_name} has invited you to join {organization_name} as a {role} on OrgMeet.

{f'Message from {inviter_name}: {message}' if message else ''}

To accept this invitation, click the link below or copy it into your browser:

{invite_url}

This invitation will expire in 7 days.

If you already have an OrgMeet account, you can log in and then accept the invitation.
If you don't have an account yet, you'll be able to create one when you click the link.

Best regards,
The OrgMeet Team
"""

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; padding: 20px 0; }}
        .logo {{ font-size: 24px; font-weight: bold; color: #2563eb; }}
        .content {{ background: #f8fafc; border-radius: 12px; padding: 30px; margin: 20px 0; }}
        .button {{ display: inline-block; background: #2563eb; color: white !important; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
        .footer {{ text-align: center; color: #64748b; font-size: 14px; padding: 20px 0; }}
        .message-box {{ background: white; border-left: 4px solid #2563eb; padding: 15px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">OrgMeet</div>
        </div>
        <div class="content">
            <h2>You're Invited!</h2>
            <p><strong>{inviter_name}</strong> has invited you to join <strong>{organization_name}</strong> as a <strong>{role}</strong>.</p>
            {f'<div class="message-box"><p><em>"{message}"</em></p><p>- {inviter_name}</p></div>' if message else ''}
            <p style="text-align: center;">
                <a href="{invite_url}" class="button">Accept Invitation</a>
            </p>
            <p style="font-size: 14px; color: #64748b;">This invitation will expire in 7 days.</p>
            <p style="font-size: 14px; color: #64748b;">If the button doesn't work, copy and paste this link into your browser:<br>
            <a href="{invite_url}">{invite_url}</a></p>
        </div>
        <div class="footer">
            <p>OrgMeet - Meeting governance made simple</p>
        </div>
    </div>
</body>
</html>
"""

        return await self.send_email(to, subject, body, html)

    async def send_meeting_reminder(
        self,
        to: str,
        meeting_title: str,
        meeting_time: datetime,
        meeting_url: str,
        organization_name: str
    ) -> bool:
        """
        Send a meeting reminder email.

        Args:
            to: Recipient email address
            meeting_title: Title of the meeting
            meeting_time: When the meeting starts
            meeting_url: URL to join the meeting
            organization_name: Name of the organization
        """
        formatted_time = meeting_time.strftime("%A, %B %d, %Y at %I:%M %p")

        subject = f"Reminder: {meeting_title} - {organization_name}"

        body = f"""Hello,

This is a reminder about an upcoming meeting:

Meeting: {meeting_title}
Organization: {organization_name}
Time: {formatted_time}

Join the meeting: {meeting_url}

Best regards,
The OrgMeet Team
"""

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; padding: 20px 0; }}
        .logo {{ font-size: 24px; font-weight: bold; color: #2563eb; }}
        .content {{ background: #f8fafc; border-radius: 12px; padding: 30px; margin: 20px 0; }}
        .meeting-info {{ background: white; border-radius: 8px; padding: 20px; margin: 20px 0; }}
        .button {{ display: inline-block; background: #2563eb; color: white !important; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
        .footer {{ text-align: center; color: #64748b; font-size: 14px; padding: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">OrgMeet</div>
        </div>
        <div class="content">
            <h2>Meeting Reminder</h2>
            <div class="meeting-info">
                <p><strong>Meeting:</strong> {meeting_title}</p>
                <p><strong>Organization:</strong> {organization_name}</p>
                <p><strong>Time:</strong> {formatted_time}</p>
            </div>
            <p style="text-align: center;">
                <a href="{meeting_url}" class="button">Join Meeting</a>
            </p>
        </div>
        <div class="footer">
            <p>OrgMeet - Meeting governance made simple</p>
        </div>
    </div>
</body>
</html>
"""

        return await self.send_email(to, subject, body, html)


# Singleton instance
email_service = EmailService()


async def send_email(to: str, subject: str, body: str, html: Optional[str] = None) -> bool:
    """Convenience function to send email using the singleton service."""
    return await email_service.send_email(to, subject, body, html)


async def send_invitation_email(
    to: str,
    organization_name: str,
    inviter_name: str,
    role: str,
    invite_token: str,
    message: Optional[str] = None
) -> bool:
    """Convenience function to send invitation email."""
    return await email_service.send_invitation_email(
        to, organization_name, inviter_name, role, invite_token, message
    )


async def send_meeting_reminder(
    to: str,
    meeting_title: str,
    meeting_time: datetime,
    meeting_url: str,
    organization_name: str
) -> bool:
    """Convenience function to send meeting reminder."""
    return await email_service.send_meeting_reminder(
        to, meeting_title, meeting_time, meeting_url, organization_name
    )
