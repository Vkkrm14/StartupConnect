"""Notification Service for TrustGraph"""

from typing import Dict, Any, List
import logging
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Notification service for sending emails, push notifications, and in-app notifications
    
    In production:
    - Email: SendGrid, AWS SES, or Mailgun
    - Push: Firebase Cloud Messaging (FCM) or OneSignal
    - SMS: Twilio
    """
    
    def __init__(self):
        self.email_enabled = settings.EMAIL_ENABLED
        self.push_enabled = settings.PUSH_ENABLED
    
    # ==========================================
    # Intro Request Notifications
    # ==========================================
    
    async def send_intro_request_notification(
        self,
        user_id: str,
        user_email: str,
        user_name: str,
        intro_data: Dict[str, Any]
    ):
        """
        Send notification when user receives an intro request
        
        Args:
            user_id: User receiving the notification
            user_email: User's email address
            user_name: User's name
            intro_data: Intro request data
        """
        try:
            # Get requester info
            founder_name = intro_data.get('founder_name', 'Someone')
            investor_name = intro_data.get('investor_name', 'an investor')
            message = intro_data.get('message', '')
            
            # Email notification
            if self.email_enabled:
                subject = f"🤝 New Introduction Request from {founder_name}"
                
                body = f"""
                <html>
                  <body style="font-family: Arial, sans-serif;">
                    <h2>Hi {user_name},</h2>
                    
                    <p>You have a new introduction request on TrustGraph!</p>
                    
                    <div style="background-color: #f5f5f5; padding: 16px; border-radius: 8px; margin: 16px 0;">
                      <p><strong>{founder_name}</strong> is requesting an introduction to <strong>{investor_name}</strong>.</p>
                      
                      {f'<p style="font-style: italic;">"{message}"</p>' if message else ''}
                    </div>
                    
                    <p>You are part of the trust path for this introduction. Please review and approve or decline this request.</p>
                    
                    <a href="{settings.WEB_APP_URL}/intros/{intro_data['intro_id']}" 
                       style="display: inline-block; background-color: #6366F1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 16px 0;">
                      Review Request
                    </a>
                    
                    <p style="color: #666; font-size: 12px; margin-top: 32px;">
                      You're receiving this because you're part of the TrustGraph network.
                    </p>
                  </body>
                </html>
                """
                
                await self._send_email(
                    to_email=user_email,
                    subject=subject,
                    html_body=body
                )
                logger.info(f"✅ Sent intro request notification to {user_email}")
            
            # Push notification
            if self.push_enabled:
                await self._send_push_notification(
                    user_id=user_id,
                    title="New Introduction Request",
                    body=f"{founder_name} wants you to help with an introduction",
                    data={"intro_id": intro_data['intro_id'], "type": "intro_request"}
                )
            
        except Exception as e:
            logger.error(f"❌ Failed to send intro request notification: {str(e)}")
    
    async def send_intro_approved_notification(
        self,
        user_id: str,
        user_email: str,
        user_name: str,
        intro_data: Dict[str, Any],
        approver_name: str
    ):
        """Notify when someone approves an intro in the chain"""
        try:
            if self.email_enabled:
                subject = f"✅ {approver_name} approved your introduction request"
                
                body = f"""
                <html>
                  <body style="font-family: Arial, sans-serif;">
                    <h2>Great news, {user_name}!</h2>
                    
                    <p><strong>{approver_name}</strong> has approved your introduction request.</p>
                    
                    <p>Your request is moving forward in the introduction chain.</p>
                    
                    <a href="{settings.WEB_APP_URL}/intros/{intro_data['intro_id']}" 
                       style="display: inline-block; background-color: #10B981; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">
                      View Status
                    </a>
                  </body>
                </html>
                """
                
                await self._send_email(
                    to_email=user_email,
                    subject=subject,
                    html_body=body
                )
                logger.info(f"✅ Sent approval notification to {user_email}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send approval notification: {str(e)}")
    
    async def send_intro_declined_notification(
        self,
        user_id: str,
        user_email: str,
        user_name: str,
        intro_data: Dict[str, Any],
        decliner_name: str,
        reason: str = None
    ):
        """Notify when someone declines an intro request"""
        try:
            if self.email_enabled:
                subject = f"Introduction request declined"
                
                body = f"""
                <html>
                  <body style="font-family: Arial, sans-serif;">
                    <h2>Hi {user_name},</h2>
                    
                    <p>Unfortunately, <strong>{decliner_name}</strong> has declined your introduction request.</p>
                    
                    {f'<p><em>Reason: {reason}</em></p>' if reason else ''}
                    
                    <p>You can try reaching out through a different path or building more connections.</p>
                    
                    <a href="{settings.WEB_APP_URL}/search" 
                       style="display: inline-block; background-color: #6366F1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">
                      Find Alternative Paths
                    </a>
                  </body>
                </html>
                """
                
                await self._send_email(
                    to_email=user_email,
                    subject=subject,
                    html_body=body
                )
                logger.info(f"✅ Sent decline notification to {user_email}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send decline notification: {str(e)}")
    
    async def send_intro_completed_notification(
        self,
        user_id: str,
        user_email: str,
        user_name: str,
        intro_data: Dict[str, Any]
    ):
        """Notify when intro chain is completed"""
        try:
            if self.email_enabled:
                founder_name = intro_data.get('founder_name', 'The founder')
                investor_name = intro_data.get('investor_name', 'the investor')
                
                subject = f"🎉 Introduction completed!"
                
                body = f"""
                <html>
                  <body style="font-family: Arial, sans-serif;">
                    <h2>Success, {user_name}!</h2>
                    
                    <p>The introduction between <strong>{founder_name}</strong> and <strong>{investor_name}</strong> has been completed!</p>
                    
                    <p>All connectors in the chain have approved, and the introduction is now active.</p>
                    
                    <p style="color: #10B981; font-weight: bold;">✅ Your trust score has been boosted for helping with this introduction!</p>
                    
                    <a href="{settings.WEB_APP_URL}/profile" 
                       style="display: inline-block; background-color: #6366F1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">
                      View Your Profile
                    </a>
                  </body>
                </html>
                """
                
                await self._send_email(
                    to_email=user_email,
                    subject=subject,
                    html_body=body
                )
                logger.info(f"✅ Sent completion notification to {user_email}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send completion notification: {str(e)}")
    
    # ==========================================
    # Trust Network Notifications
    # ==========================================
    
    async def send_trust_connection_notification(
        self,
        user_id: str,
        user_email: str,
        user_name: str,
        connector_name: str
    ):
        """Notify when someone adds you to their trust network"""
        try:
            if self.email_enabled:
                subject = f"{connector_name} added you to their trust network"
                
                body = f"""
                <html>
                  <body style="font-family: Arial, sans-serif;">
                    <h2>Hi {user_name},</h2>
                    
                    <p><strong>{connector_name}</strong> has added you to their trust network on TrustGraph.</p>
                    
                    <p>This means they trust you and you may receive introduction requests through them.</p>
                    
                    <a href="{settings.WEB_APP_URL}/profile/{user_id}" 
                       style="display: inline-block; background-color: #6366F1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">
                      View Your Network
                    </a>
                  </body>
                </html>
                """
                
                await self._send_email(
                    to_email=user_email,
                    subject=subject,
                    html_body=body
                )
            
        except Exception as e:
            logger.error(f"❌ Failed to send trust connection notification: {str(e)}")
    
    # ==========================================
    # Core Email/Push Methods
    # ==========================================
    
    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str = None
    ):
        """
        Send email via SMTP
        
        In production, replace with:
        - SendGrid API
        - AWS SES
        - Mailgun
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = settings.EMAIL_FROM
            msg['To'] = to_email
            
            # Add text version
            if text_body:
                part1 = MIMEText(text_body, 'plain')
                msg.attach(part1)
            
            # Add HTML version
            part2 = MIMEText(html_body, 'html')
            msg.attach(part2)
            
            # Send via SMTP (development only)
            if settings.SMTP_HOST:
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    if settings.SMTP_TLS:
                        server.starttls()
                    if settings.SMTP_USER:
                        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.send_message(msg)
                    logger.info(f"📧 Email sent to {to_email}")
            else:
                # Log email in development
                logger.info(f"📧 [DEV] Would send email to {to_email}: {subject}")
            
        except Exception as e:
            logger.error(f"❌ Email send failed: {str(e)}")
            raise
    
    async def _send_push_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        data: Dict[str, Any] = None
    ):
        """
        Send push notification
        
        In production, implement with:
        - Firebase Cloud Messaging (FCM)
        - OneSignal
        - APNs for iOS
        """
        try:
            # TODO: Implement FCM/OneSignal integration
            logger.info(f"🔔 [DEV] Would send push to {user_id}: {title}")
            
        except Exception as e:
            logger.error(f"❌ Push notification failed: {str(e)}")

# Singleton instance
notification_service = NotificationService()
