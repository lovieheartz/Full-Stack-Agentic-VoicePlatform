"""
Google Calendar Integration with OAuth Flow + Google Meet Link Generation
Auto-syncs booking events to Google Calendar when appointments are created
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
import secrets
import httpx
from typing import Optional

from app.database import get_db
from app.models import Integration
from app.encryption import encryption_service
from app.security import get_current_user
from app.config import settings
from app.schemas import IntegrationResponse, CompleteOAuthRequest

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# GOOGLE CALENDAR CLIENT
# ============================================================================

class GoogleCalendarClient:
    """Client for Google Calendar API"""

    def __init__(self, access_token: str, refresh_token: str, client_id: str, client_secret: str):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_base_url = "https://www.googleapis.com/calendar/v3"

    async def refresh_access_token(self) -> str:
        """Refresh expired access token"""
        token_url = "https://oauth2.googleapis.com/token"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                token_url,
                data={
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token"
                }
            )
            response.raise_for_status()
            token_data = response.json()

        return token_data.get("access_token")

    async def create_event(
        self,
        summary: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        attendee_email: Optional[str] = None,
        add_google_meet: bool = True,
        timezone: str = "Asia/Kolkata"
    ) -> dict:
        """
        Create a calendar event in Google Calendar

        Args:
            summary: Event title
            description: Event description
            start_time: Event start datetime
            end_time: Event end datetime
            attendee_email: Optional attendee email
            add_google_meet: Whether to add Google Meet conference link
            timezone: Timezone for the event

        Returns:
            dict: Event details including htmlLink, id, and hangoutLink
        """
        # Format datetime for Google Calendar API
        start_str = start_time.strftime("%Y-%m-%dT%H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%dT%H:%M:%S")

        event_data = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start_str,
                "timeZone": timezone
            },
            "end": {
                "dateTime": end_str,
                "timeZone": timezone
            }
        }

        # Add Google Meet conference link
        if add_google_meet:
            event_data["conferenceData"] = {
                "createRequest": {
                    "requestId": str(uuid.uuid4()),
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            }

        # Add attendee if provided
        if attendee_email:
            event_data["attendees"] = [{"email": attendee_email}]

        # Create event
        create_url = f"{self.api_base_url}/calendars/primary/events"
        params = {"conferenceDataVersion": "1"} if add_google_meet else {}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                create_url,
                json=event_data,
                params=params,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
            )

            # Auto-refresh token if expired
            if response.status_code == 401:
                logger.info("Token expired, refreshing...")
                self.access_token = await self.refresh_access_token()

                # Retry with new token
                response = await client.post(
                    create_url,
                    json=event_data,
                    params=params,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    }
                )

            response.raise_for_status()
            return response.json()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def create_google_calendar_event(
    client_id: str,
    client_secret: str,
    access_token: str,
    refresh_token: str,
    summary: str,
    description: str,
    start_time: datetime,
    end_time: datetime,
    attendee_email: Optional[str] = None,
    add_google_meet: bool = True,
    timezone: str = "Asia/Kolkata"
) -> dict:
    """Helper function to create a Google Calendar event"""
    client = GoogleCalendarClient(access_token, refresh_token, client_id, client_secret)
    return await client.create_event(
        summary=summary,
        description=description,
        start_time=start_time,
        end_time=end_time,
        attendee_email=attendee_email,
        add_google_meet=add_google_meet,
        timezone=timezone
    )


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/integrations/google-calendar/connect")
async def connect_google_calendar(
    request: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🚀 Connect Google Calendar - Initiate OAuth Flow

    Request:
    {
        "client_id": "123456789.apps.googleusercontent.com",
        "client_secret": "GOCSPX-xxxxx"
    }

    Response:
    {
        "success": true,
        "message": "Credentials saved. Please authorize.",
        "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
        "state": "csrf_token",
        "integration_id": "uuid",
        "provider": "google_calendar"
    }
    """
    try:
        organization_id = uuid.UUID(current_user["organization_id"])

        logger.info(f"=== CONNECT GOOGLE CALENDAR ===")
        logger.info(f"Organization: {organization_id}")

        # Generate CSRF state token
        state = secrets.token_urlsafe(32)

        # Prepare encrypted credentials
        credentials_data = {
            "client_id": request.get("client_id"),
            "client_secret": request.get("client_secret"),
            "oauth_state": state,
            "oauth_user_id": current_user.get("sub"),
            "oauth_initiated_at": datetime.utcnow().isoformat()
        }

        encrypted_config = encryption_service.encrypt_credentials(credentials_data)

        # Check if integration exists
        existing = db.query(Integration).filter(
            Integration.organization_id == organization_id,
            Integration.type == "meeting",
            Integration.provider == "google_calendar"
        ).first()

        if existing:
            existing.config = encrypted_config
            existing.is_active = True
            existing.is_connected = False
            integration_id = str(existing.id)
            logger.info(f"Updated integration: {integration_id}")
        else:
            new_integration = Integration(
                organization_id=organization_id,
                name="Google Calendar",
                type="meeting",
                provider="google_calendar",
                config=encrypted_config,
                is_active=True,
                is_connected=False
            )
            db.add(new_integration)
            db.flush()
            integration_id = str(new_integration.id)
            logger.info(f"Created integration: {integration_id}")

        db.commit()

        # Build OAuth URL
        redirect_uri = f"{settings.FRONTEND_URL}/oauth/callback"
        scope = "https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/calendar"

        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={request.get('client_id')}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope={scope}"
            f"&access_type=offline"
            f"&state={state}"
            f"&prompt=consent"
        )

        logger.info(f"✅ OAuth URL generated")

        return {
            "success": True,
            "message": "Google Calendar credentials saved. Please authorize in popup.",
            "authorization_url": auth_url,
            "state": state,
            "integration_id": integration_id,
            "provider": "google_calendar"
        }

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect Google Calendar: {str(e)}"
        )


@router.post("/integrations/google-calendar/oauth/complete")
async def complete_google_calendar_oauth(
    request: CompleteOAuthRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ✅ Complete OAuth - Exchange authorization code for tokens

    Request:
    {
        "code": "authorization_code_from_google",
        "state": "csrf_token"
    }

    Response:
    {
        "success": true,
        "message": "Google Calendar connected successfully!",
        "expires_at": "2025-01-18T12:00:00",
        "integration_id": "uuid"
    }
    """
    logger.info(f"=== COMPLETE OAUTH ===")
    logger.info(f"Organization: {current_user['organization_id']}")

    # Get integration
    integration = db.query(Integration).filter(
        Integration.organization_id == uuid.UUID(current_user["organization_id"]),
        Integration.type == "meeting",
        Integration.provider == "google_calendar",
        Integration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(
            status_code=404,
            detail="Google Calendar integration not found. Please connect first."
        )

    # Decrypt credentials
    credentials = encryption_service.decrypt_credentials(integration.config)

    # Verify CSRF state
    stored_state = credentials.get("oauth_state")
    if not stored_state or stored_state != request.state:
        raise HTTPException(
            status_code=400,
            detail="Invalid state parameter. Possible CSRF attack."
        )

    client_id = credentials.get("client_id")
    client_secret = credentials.get("client_secret")

    # Exchange code for tokens
    redirect_uri = f"{settings.FRONTEND_URL}/oauth/callback"
    token_url = "https://oauth2.googleapis.com/token"

    logger.info("Exchanging code for tokens...")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                token_url,
                data={
                    "code": request.code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            response.raise_for_status()
            token_data = response.json()

        # Validate response
        if "error" in token_data:
            raise HTTPException(
                status_code=400,
                detail=f"Google OAuth error: {token_data.get('error')}"
            )

        if "access_token" not in token_data:
            raise HTTPException(
                status_code=400,
                detail="Missing access_token in response"
            )

        # Calculate expiration
        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Update credentials with tokens
        credentials["access_token"] = token_data["access_token"]
        credentials["refresh_token"] = token_data.get("refresh_token", "")
        credentials["token_expires_at"] = expires_at.isoformat()
        credentials["oauth_completed"] = True
        credentials["oauth_completed_at"] = datetime.utcnow().isoformat()

        # Remove temporary OAuth state
        credentials.pop("oauth_state", None)
        credentials.pop("oauth_user_id", None)
        credentials.pop("oauth_initiated_at", None)

        # Save encrypted credentials with tokens
        integration.config = encryption_service.encrypt_credentials(credentials)
        integration.is_connected = True
        integration.last_sync_at = datetime.utcnow()
        db.commit()

        logger.info(f"✅ OAuth completed! Tokens saved in database.")

        return {
            "success": True,
            "message": "Google Calendar connected successfully! Events will auto-sync.",
            "expires_at": expires_at.isoformat(),
            "integration_id": str(integration.id)
        }

    except httpx.HTTPStatusError as e:
        error_detail = e.response.json() if e.response else str(e)
        logger.error(f"❌ Token exchange failed: {error_detail}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to exchange code: {error_detail}"
        )
    except Exception as e:
        logger.error(f"❌ OAuth error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"OAuth failed: {str(e)}"
        )


@router.post("/integrations/google-calendar/create-event")
async def create_event_endpoint(
    request: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📅 Create Google Calendar Event (Internal use - called by booking system)

    Request:
    {
        "summary": "Meeting with Customer",
        "description": "Scheduled meeting",
        "start_time": "2025-12-25T14:30:00",
        "end_time": "2025-12-25T15:30:00",
        "attendee_email": "customer@example.com",
        "add_google_meet": true,
        "timezone": "Asia/Kolkata"
    }
    """
    try:
        organization_id = uuid.UUID(current_user["organization_id"])

        logger.info(f"=== CREATE GOOGLE CALENDAR EVENT ===")

        # Get integration
        integration = db.query(Integration).filter(
            Integration.organization_id == organization_id,
            Integration.type == "meeting",
            Integration.provider == "google_calendar",
            Integration.is_active == True,
            Integration.is_connected == True
        ).first()

        if not integration or not integration.config:
            raise HTTPException(
                status_code=404,
                detail="Google Calendar not connected."
            )

        # Decrypt credentials
        credentials = encryption_service.decrypt_credentials(integration.config)

        # Parse datetime
        start_time = datetime.fromisoformat(request.get("start_time"))
        end_time = datetime.fromisoformat(request.get("end_time"))

        # Create event
        event = await create_google_calendar_event(
            client_id=credentials.get("client_id"),
            client_secret=credentials.get("client_secret"),
            access_token=credentials.get("access_token"),
            refresh_token=credentials.get("refresh_token"),
            summary=request.get("summary"),
            description=request.get("description", ""),
            start_time=start_time,
            end_time=end_time,
            attendee_email=request.get("attendee_email"),
            add_google_meet=request.get("add_google_meet", True),
            timezone=request.get("timezone", "Asia/Kolkata")
        )

        logger.info(f"✅ Google Calendar event created: {event.get('id')}")

        return {
            "success": True,
            "message": "Event created successfully",
            "event_id": event.get("id"),
            "event_link": event.get("htmlLink"),
            "google_meet_link": event.get("hangoutLink")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating event: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create event: {str(e)}"
        )
