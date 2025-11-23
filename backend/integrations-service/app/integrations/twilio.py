import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.models import Integration
from app.schemas import (
    TwilioSMSCredentialsRequest,
    IntegrationResponse,
    SendSMSRequest,
    SendSMSResponse
)
from app.security import get_current_user, get_current_user_flexible
from app.encryption import encryption_service

logger = logging.getLogger(__name__)

# Create router for Twilio endpoints
router = APIRouter()


# ============= TWILIO SMS API ENDPOINTS =============

@router.post("/integrations/twilio-sms", response_model=IntegrationResponse)
async def store_twilio_sms_credentials(
    request: TwilioSMSCredentialsRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Store Twilio SMS credentials for the organization

    **Request body:**
    - account_sid: Twilio Account SID
    - auth_token: Twilio Auth Token
    - phone_number: Twilio phone number with country code (e.g., +1234567890)
    """
    try:
        organization_id = current_user["organization_id"]
        logger.info(f"Storing Twilio SMS credentials for organization: {organization_id}")

        # Prepare credentials dict
        credentials = {
            "account_sid": request.account_sid,
            "auth_token": request.auth_token,
            "phone_number": request.phone_number
        }

        # Encrypt credentials
        encrypted_config = encryption_service.encrypt_credentials(credentials)

        # Check if integration already exists
        existing_integration = db.query(Integration).filter(
            Integration.organization_id == uuid.UUID(organization_id),
            Integration.type == "sms",
            Integration.provider == "twilio"
        ).first()

        if existing_integration:
            # Update existing integration
            existing_integration.config = encrypted_config
            existing_integration.is_connected = True
            db.commit()
            db.refresh(existing_integration)

            logger.info(f"Updated Twilio SMS integration: {existing_integration.id}")

            return IntegrationResponse(
                id=str(existing_integration.id),
                name=existing_integration.name,
                type=existing_integration.type,
                provider=existing_integration.provider,
                is_active=existing_integration.is_active,
                is_connected=existing_integration.is_connected,
                created_at=existing_integration.created_at.isoformat(),
                message="Twilio SMS credentials updated successfully"
            )
        else:
            # Create new integration
            new_integration = Integration(
                organization_id=uuid.UUID(organization_id),
                name="Twilio SMS",
                type="sms",
                provider="twilio",
                config=encrypted_config,
                is_active=True,
                is_connected=True
            )
            db.add(new_integration)
            db.commit()
            db.refresh(new_integration)

            logger.info(f"Created new Twilio SMS integration: {new_integration.id}")

            return IntegrationResponse(
                id=str(new_integration.id),
                name=new_integration.name,
                type=new_integration.type,
                provider=new_integration.provider,
                is_active=new_integration.is_active,
                is_connected=new_integration.is_connected,
                created_at=new_integration.created_at.isoformat(),
                message="Twilio SMS credentials stored successfully"
            )

    except Exception as e:
        logger.error(f"Error storing Twilio SMS credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to store credentials: {str(e)}")


@router.post("/integrations/send-sms", response_model=SendSMSResponse)
async def send_sms(
    request: SendSMSRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_flexible)
):
    """
    Send SMS using Twilio (LLM agent function calling)

    **Request body:**
    - phone_number: Recipient phone number with country code (e.g., +1234567890)
    - message: SMS message content
    """
    try:
        organization_id = current_user["organization_id"]
        logger.info(f"Sending SMS for organization: {organization_id}")

        # Fetch Twilio credentials from integrations table
        integration = db.query(Integration).filter(
            Integration.organization_id == uuid.UUID(organization_id),
            Integration.type == "sms",
            Integration.provider == "twilio",
            Integration.is_active == True
        ).first()

        if not integration:
            raise HTTPException(
                status_code=404,
                detail="Twilio SMS integration not found or not active. Please configure Twilio SMS in integrations first."
            )

        # Decrypt credentials
        try:
            credentials = encryption_service.decrypt_credentials(integration.config)
        except Exception as e:
            logger.error(f"Failed to decrypt Twilio credentials: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to decrypt Twilio credentials")

        # Initialize Twilio client
        try:
            from twilio.rest import Client
            twilio_client = Client(
                credentials["account_sid"],
                credentials["auth_token"]
            )
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to initialize Twilio client")

        # Send SMS
        try:
            message = twilio_client.messages.create(
                body=request.message,
                from_=credentials["phone_number"],
                to=request.phone_number
            )

            logger.info(f"SMS sent successfully. SID: {message.sid}")

            return SendSMSResponse(
                success=True,
                message="SMS sent successfully",
                sid=message.sid
            )

        except Exception as e:
            logger.error(f"Failed to send SMS: {str(e)}")
            return SendSMSResponse(
                success=False,
                message=f"Failed to send SMS: {str(e)}",
                sid=None
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in send_sms: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {str(e)}")
