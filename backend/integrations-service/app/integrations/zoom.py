import logging
from datetime import datetime, timedelta
import httpx
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.models import Integration
from app.schemas import (
    ZoomCredentialsRequest,
    IntegrationResponse,
    CreateZoomMeetingRequest,
    CreateZoomMeetingResponse
)
from app.security import get_current_user, get_current_user_flexible
from app.encryption import encryption_service

logger = logging.getLogger(__name__)

# Create router for Zoom endpoints
router = APIRouter()


class ZoomClient:
    """Zoom API client for creating meetings"""

    def __init__(self, account_id: str, client_id: str, client_secret: str):
        self.account_id = account_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://api.zoom.us/v2"
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

    async def get_access_token(self) -> str:
        """Get OAuth access token using Server-to-Server OAuth"""
        # Check if token is still valid
        if self.access_token and self.token_expiry and datetime.utcnow() < self.token_expiry:
            return self.access_token

        logger.info("Fetching new Zoom access token")

        token_url = "https://zoom.us/oauth/token"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                params={
                    "grant_type": "account_credentials",
                    "account_id": self.account_id
                },
                auth=(self.client_id, self.client_secret)
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                # Token expires in 1 hour, refresh 5 minutes before
                self.token_expiry = datetime.utcnow() + timedelta(seconds=data["expires_in"] - 300)
                logger.info("Zoom access token obtained successfully")
                return self.access_token
            else:
                logger.error(f"Failed to get Zoom access token: {response.status_code} - {response.text}")
                raise Exception(f"Failed to authenticate with Zoom: {response.status_code}")

    async def create_meeting(
        self,
        topic: str,
        start_time: str,
        duration: int = 60,
        timezone: str = "UTC",
        agenda: Optional[str] = None
    ) -> dict:
        """
        Create a Zoom meeting

        Args:
            topic: Meeting title
            start_time: Start time in ISO format (e.g., "2024-01-15T10:00:00Z")
            duration: Meeting duration in minutes (default 60)
            timezone: Timezone for the meeting (default UTC)
            agenda: Optional meeting agenda

        Returns:
            dict: Meeting details including join_url, meeting_id, etc.
        """
        access_token = await self.get_access_token()

        meeting_data = {
            "topic": topic,
            "type": 2,  # Scheduled meeting
            "start_time": start_time,
            "duration": duration,
            "timezone": timezone,
            "agenda": agenda or f"Scheduled meeting: {topic}",
            "settings": {
                "host_video": True,
                "participant_video": True,
                "join_before_host": False,
                "mute_upon_entry": False,
                "watermark": False,
                "audio": "both",
                "auto_recording": "none"
            }
        }

        logger.info(f"Creating Zoom meeting: {topic}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/users/me/meetings",
                json=meeting_data,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
            )

            if response.status_code == 201:
                meeting = response.json()
                logger.info(f"Zoom meeting created successfully: {meeting['id']}")
                return {
                    "meeting_id": meeting["id"],
                    "topic": meeting["topic"],
                    "start_time": meeting["start_time"],
                    "duration": meeting["duration"],
                    "timezone": meeting["timezone"],
                    "join_url": meeting["join_url"],
                    "password": meeting.get("password"),
                    "host_email": meeting.get("host_email")
                }
            else:
                logger.error(f"Failed to create Zoom meeting: {response.status_code} - {response.text}")
                raise Exception(f"Failed to create Zoom meeting: {response.status_code}")


async def create_zoom_meeting(
    account_id: str,
    client_id: str,
    client_secret: str,
    topic: str,
    start_time: str,
    duration: int = 60,
    timezone: str = "UTC",
    agenda: Optional[str] = None
) -> dict:
    """Helper function to create a Zoom meeting"""
    client = ZoomClient(account_id, client_id, client_secret)
    return await client.create_meeting(topic, start_time, duration, timezone, agenda)


# ============= ZOOM API ENDPOINTS =============

@router.post("/integrations/zoom", response_model=IntegrationResponse)
async def store_zoom_credentials(
    request: ZoomCredentialsRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Store Zoom credentials (Server-to-Server OAuth)

    **Request body:**
    - account_id: Zoom Account ID
    - client_id: Zoom Client ID
    - client_secret: Zoom Client Secret
    """
    try:
        organization_id = current_user["organization_id"]
        logger.info(f"Storing Zoom credentials for organization: {organization_id}")

        # Prepare credentials for encryption
        credentials = {
            "account_id": request.account_id,
            "client_id": request.client_id,
            "client_secret": request.client_secret
        }

        # Encrypt credentials
        encrypted_config = encryption_service.encrypt_credentials(credentials)

        # Check if Zoom integration already exists
        existing_integration = db.query(Integration).filter(
            Integration.organization_id == uuid.UUID(organization_id),
            Integration.type == "meeting",
            Integration.provider == "zoom"
        ).first()

        if existing_integration:
            # Update existing integration
            existing_integration.config = encrypted_config
            existing_integration.is_connected = True
            db.commit()
            db.refresh(existing_integration)

            logger.info(f"Updated Zoom integration: {existing_integration.id}")

            return IntegrationResponse(
                id=str(existing_integration.id),
                name=existing_integration.name,
                type=existing_integration.type,
                provider=existing_integration.provider,
                is_active=existing_integration.is_active,
                is_connected=existing_integration.is_connected,
                created_at=existing_integration.created_at.isoformat(),
                message="Zoom credentials updated successfully"
            )
        else:
            # Create new integration
            new_integration = Integration(
                organization_id=uuid.UUID(organization_id),
                name="Zoom Meetings",
                type="meeting",
                provider="zoom",
                config=encrypted_config,
                is_active=True,
                is_connected=True
            )
            db.add(new_integration)
            db.commit()
            db.refresh(new_integration)

            logger.info(f"Created new Zoom integration: {new_integration.id}")

            return IntegrationResponse(
                id=str(new_integration.id),
                name=new_integration.name,
                type=new_integration.type,
                provider=new_integration.provider,
                is_active=new_integration.is_active,
                is_connected=new_integration.is_connected,
                created_at=new_integration.created_at.isoformat(),
                message="Zoom credentials stored successfully"
            )

    except Exception as e:
        logger.error(f"Error storing Zoom credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to store credentials: {str(e)}")


@router.post("/integrations/create-zoom-meeting", response_model=CreateZoomMeetingResponse)
async def create_zoom_meeting_endpoint(
    request: CreateZoomMeetingRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_flexible)
):
    """
    Create a Zoom meeting (LLM agent function calling)

    **Request body:**
    - topic: Meeting title
    - start_time: Start time in ISO format (e.g., "2024-01-15T10:00:00Z")
    - duration: Meeting duration in minutes (default 60)
    - timezone: Timezone for the meeting (default UTC)
    - agenda: Optional meeting agenda
    """
    try:
        organization_id = current_user["organization_id"]
        logger.info(f"Creating Zoom meeting for organization: {organization_id}")

        # Fetch Zoom credentials from integrations table
        integration = db.query(Integration).filter(
            Integration.organization_id == uuid.UUID(organization_id),
            Integration.type == "meeting",
            Integration.provider == "zoom",
            Integration.is_active == True
        ).first()

        if not integration:
            raise HTTPException(
                status_code=404,
                detail="Zoom integration not found or not active. Please configure Zoom in integrations first."
            )

        # Decrypt credentials
        try:
            credentials = encryption_service.decrypt_credentials(integration.config)
        except Exception as e:
            logger.error(f"Failed to decrypt Zoom credentials: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to decrypt Zoom credentials")

        # Create Zoom meeting
        try:
            meeting = await create_zoom_meeting(
                account_id=credentials["account_id"],
                client_id=credentials["client_id"],
                client_secret=credentials["client_secret"],
                topic=request.topic,
                start_time=request.start_time,
                duration=request.duration,
                timezone=request.timezone,
                agenda=request.agenda
            )

            logger.info(f"Zoom meeting created successfully. Meeting ID: {meeting['meeting_id']}")

            return CreateZoomMeetingResponse(
                success=True,
                message="Zoom meeting created successfully",
                meeting_id=str(meeting["meeting_id"]),
                join_url=meeting["join_url"],
                password=meeting.get("password"),
                start_time=meeting["start_time"]
            )

        except Exception as e:
            logger.error(f"Failed to create Zoom meeting: {str(e)}")
            return CreateZoomMeetingResponse(
                success=False,
                message=f"Failed to create Zoom meeting: {str(e)}",
                meeting_id=None,
                join_url=None,
                password=None,
                start_time=None
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_zoom_meeting: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create Zoom meeting: {str(e)}")
