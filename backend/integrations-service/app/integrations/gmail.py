import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.models import Integration
from app.schemas import (
    GmailCredentialsRequest,
    IntegrationResponse,
    SendEmailRequest,
    SendEmailResponse
)
from app.security import get_current_user, get_current_user_flexible
from app.encryption import encryption_service

logger = logging.getLogger(__name__)

# Create router for Gmail endpoints
router = APIRouter()


class GmailClient:
    """Gmail SMTP client for sending emails using App Password"""

    def __init__(self, email: str, app_password: str):
        self.email = email
        self.app_password = app_password
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> dict:
        """
        Send an email via Gmail SMTP

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text email body
            html_body: Optional HTML email body

        Returns:
            dict: Success status and message
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email
            msg['To'] = to_email
            msg['Subject'] = subject

            # Add plain text part
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)

            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)

            # Connect to Gmail SMTP server
            logger.info(f"Connecting to Gmail SMTP server: {self.smtp_server}:{self.smtp_port}")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Upgrade to secure connection
                server.login(self.email, self.app_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return {
                "success": True,
                "message": "Email sent successfully",
                "recipient": to_email
            }

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Gmail authentication failed: {str(e)}")
            raise Exception("Gmail authentication failed. Please check your email and app password.")
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error occurred: {str(e)}")
            raise Exception(f"Failed to send email: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}")
            raise Exception(f"Failed to send email: {str(e)}")


def send_gmail_email(
    email: str,
    app_password: str,
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None
) -> dict:
    """Helper function to send an email via Gmail"""
    client = GmailClient(email, app_password)
    return client.send_email(to_email, subject, body, html_body)


# ============= GMAIL API ENDPOINTS =============

@router.post("/integrations/gmail", response_model=IntegrationResponse)
async def store_gmail_credentials(
    request: GmailCredentialsRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Store Gmail credentials (Email + App Password)

    **Request body:**
    - email: Gmail email address
    - app_password: Gmail App Password (16-character password from Google Account settings)
    """
    try:
        organization_id = current_user["organization_id"]
        logger.info(f"Storing Gmail credentials for organization: {organization_id}")

        # Prepare credentials for encryption
        credentials = {
            "email": request.email,
            "app_password": request.app_password
        }

        # Encrypt credentials
        encrypted_config = encryption_service.encrypt_credentials(credentials)

        # Check if Gmail integration already exists
        existing_integration = db.query(Integration).filter(
            Integration.organization_id == uuid.UUID(organization_id),
            Integration.type == "email",
            Integration.provider == "gmail"
        ).first()

        if existing_integration:
            # Update existing integration
            existing_integration.config = encrypted_config
            existing_integration.is_connected = True
            db.commit()
            db.refresh(existing_integration)

            logger.info(f"Updated Gmail integration: {existing_integration.id}")

            return IntegrationResponse(
                id=str(existing_integration.id),
                name=existing_integration.name,
                type=existing_integration.type,
                provider=existing_integration.provider,
                is_active=existing_integration.is_active,
                is_connected=existing_integration.is_connected,
                created_at=existing_integration.created_at.isoformat(),
                message="Gmail credentials updated successfully"
            )
        else:
            # Create new integration
            new_integration = Integration(
                organization_id=uuid.UUID(organization_id),
                name="Gmail",
                type="email",
                provider="gmail",
                config=encrypted_config,
                is_active=True,
                is_connected=True
            )
            db.add(new_integration)
            db.commit()
            db.refresh(new_integration)

            logger.info(f"Created new Gmail integration: {new_integration.id}")

            return IntegrationResponse(
                id=str(new_integration.id),
                name=new_integration.name,
                type=new_integration.type,
                provider=new_integration.provider,
                is_active=new_integration.is_active,
                is_connected=new_integration.is_connected,
                created_at=new_integration.created_at.isoformat(),
                message="Gmail credentials stored successfully"
            )

    except Exception as e:
        logger.error(f"Error storing Gmail credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to store credentials: {str(e)}")


@router.post("/integrations/send-email", response_model=SendEmailResponse)
async def send_email(
    request: SendEmailRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_flexible)
):
    """
    Send email using Gmail (LLM agent function calling)

    **Request body:**
    - to_email: Recipient email address
    - subject: Email subject
    - body: Email body (plain text)
    - html_body: Optional HTML email body
    """
    try:
        organization_id = current_user["organization_id"]
        logger.info(f"Sending email for organization: {organization_id}")

        # Fetch Gmail credentials from integrations table
        integration = db.query(Integration).filter(
            Integration.organization_id == uuid.UUID(organization_id),
            Integration.type == "email",
            Integration.provider == "gmail",
            Integration.is_active == True
        ).first()

        if not integration:
            raise HTTPException(
                status_code=404,
                detail="Gmail integration not found or not active. Please configure Gmail in integrations first."
            )

        # Decrypt credentials
        try:
            credentials = encryption_service.decrypt_credentials(integration.config)
        except Exception as e:
            logger.error(f"Failed to decrypt Gmail credentials: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to decrypt Gmail credentials")

        # Send email
        try:
            result = send_gmail_email(
                email=credentials["email"],
                app_password=credentials["app_password"],
                to_email=request.to_email,
                subject=request.subject,
                body=request.body,
                html_body=request.html_body
            )

            logger.info(f"Email sent successfully to {request.to_email}")

            return SendEmailResponse(
                success=True,
                message="Email sent successfully",
                recipient=request.to_email
            )

        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return SendEmailResponse(
                success=False,
                message=f"Failed to send email: {str(e)}",
                recipient=None
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in send_email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")
