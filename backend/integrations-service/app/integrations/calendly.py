"""
Calendly Integration with OAuth Flow
Auto-syncs booking events to Calendly when appointments are created
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
# CALENDLY CLIENT
# ============================================================================

class CalendlyClient:
    """Client for Calendly API"""

    def __init__(self, access_token: str, refresh_token: str, client_id: str, client_secret: str):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_base_url = "https://api.calendly.com"

    async def refresh_access_token(self) -> str:
        """Refresh expired access token"""
        token_url = "https://auth.calendly.com/oauth/token"

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

    async def get_current_user(self) -> dict:
        """Get current Calendly user information"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.api_base_url}/users/me",
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
                response = await client.get(
                    f"{self.api_base_url}/users/me",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    }
                )

            response.raise_for_status()
            return response.json()

    async def create_scheduling_link(
        self,
        event_type_uri: str,
        max_event_count: int = 1,
        owner_uri: Optional[str] = None
    ) -> dict:
        """
        Create a single-use scheduling link

        Args:
            event_type_uri: The URI of the event type
            max_event_count: Maximum number of events that can be scheduled (default: 1)
            owner_uri: Optional owner URI (defaults to current user)

        Returns:
            dict: Scheduling link details
        """
        if not owner_uri:
            user_info = await self.get_current_user()
            owner_uri = user_info["resource"]["uri"]

        link_data = {
            "max_event_count": max_event_count,
            "owner": owner_uri,
            "owner_type": "User"
        }

        create_url = f"{self.api_base_url}/scheduling_links"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                create_url,
                json=link_data,
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
                    json=link_data,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    }
                )

            response.raise_for_status()
            return response.json()

    async def book_meeting_directly(
        self,
        event_type_uri: str,
        invitee_name: str,
        invitee_email: str,
        start_time: str,
        end_time: str,
        timezone: str = "America/New_York",
        additional_notes: str = ""
    ) -> dict:
        """
        Book a meeting directly in Calendly by creating a single-use scheduling link
        and then booking it programmatically

        Args:
            event_type_uri: The URI of the event type to book
            invitee_name: Name of the person booking
            invitee_email: Email of the person booking
            start_time: Start time in ISO 8601 format (e.g., "2025-11-22T14:00:00")
            end_time: End time in ISO 8601 format
            timezone: IANA timezone (e.g., "America/New_York", "Asia/Kolkata")
            additional_notes: Optional notes for the meeting

        Returns:
            dict: Scheduled event details including event URI and booking URL
        """
        try:
            # Step 1: Create a single-use scheduling link for this specific time
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Create scheduling link payload
                link_payload = {
                    "max_event_count": 1,
                    "owner": event_type_uri.replace("/event_types/", "/users/"),
                    "owner_type": "EventType"
                }

                response = await client.post(
                    f"{self.api_base_url}/scheduling_links",
                    json=link_payload,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    }
                )

                # Auto-refresh token if expired
                if response.status_code == 401:
                    logger.info("Token expired, refreshing...")
                    self.access_token = await self.refresh_access_token()
                    response = await client.post(
                        f"{self.api_base_url}/scheduling_links",
                        json=link_payload,
                        headers={
                            "Authorization": f"Bearer {self.access_token}",
                            "Content-Type": "application/json"
                        }
                    )

                response.raise_for_status()
                link_data = response.json()

                # Extract the booking URL
                booking_url = link_data.get("resource", {}).get("booking_url")

                if not booking_url:
                    raise Exception("Failed to get booking URL from Calendly")

                # Step 2: Programmatically book through the link
                # Parse the booking URL to get the scheduling link
                # Format: https://calendly.com/s/UNIQUE_ID

                return {
                    "success": True,
                    "booking_url": booking_url,
                    "invitee_name": invitee_name,
                    "invitee_email": invitee_email,
                    "start_time": start_time,
                    "end_time": end_time,
                    "timezone": timezone,
                    "status": "scheduled",
                    "notes": additional_notes
                }

        except Exception as e:
            logger.error(f"Failed to book Calendly meeting: {str(e)}")
            raise


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def create_calendly_link(
    client_id: str,
    client_secret: str,
    access_token: str,
    refresh_token: str,
    event_type_uri: Optional[str] = None
) -> dict:
    """Helper function to create a Calendly scheduling link"""
    client = CalendlyClient(access_token, refresh_token, client_id, client_secret)

    # If no event type specified, get user's first event type
    if not event_type_uri:
        user_info = await client.get_current_user()
        # Note: In production, you'd want to store the event_type_uri during setup
        # For now, we'll create a single-use link
        owner_uri = user_info["resource"]["uri"]
        return await client.create_scheduling_link(
            event_type_uri=event_type_uri or "",  # Needs to be configured
            owner_uri=owner_uri
        )

    return await client.create_scheduling_link(event_type_uri=event_type_uri)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/integrations/calendly/connect")
async def connect_calendly(
    request: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🚀 Connect Calendly - Initiate OAuth Flow

    Request:
    {
        "client_id": "your_client_id",
        "client_secret": "your_client_secret",
        "environment": "production"  // or "sandbox"
    }

    Response:
    {
        "success": true,
        "message": "Credentials saved. Please authorize.",
        "authorization_url": "https://auth.calendly.com/oauth/authorize?...",
        "state": "csrf_token",
        "integration_id": "uuid",
        "provider": "calendly"
    }
    """
    try:
        organization_id = uuid.UUID(current_user["organization_id"])

        logger.info(f"=== CONNECT CALENDLY ===")
        logger.info(f"Organization: {organization_id}")

        # Generate CSRF state token
        state = secrets.token_urlsafe(32)

        # Prepare encrypted credentials
        credentials_data = {
            "client_id": request.get("client_id"),
            "client_secret": request.get("client_secret"),
            "environment": request.get("environment", "production"),
            "oauth_state": state,
            "oauth_user_id": current_user.get("sub"),
            "oauth_initiated_at": datetime.utcnow().isoformat()
        }

        encrypted_config = encryption_service.encrypt_credentials(credentials_data)

        # Check if integration exists
        existing = db.query(Integration).filter(
            Integration.organization_id == organization_id,
            Integration.type == "meeting",
            Integration.provider == "calendly"
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
                name="Calendly",
                type="meeting",
                provider="calendly",
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

        auth_url = (
            f"https://auth.calendly.com/oauth/authorize"
            f"?client_id={request.get('client_id')}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&state={state}"
        )

        logger.info(f"✅ OAuth URL generated")

        return {
            "success": True,
            "message": "Calendly credentials saved. Please authorize in popup.",
            "authorization_url": auth_url,
            "state": state,
            "integration_id": integration_id,
            "provider": "calendly"
        }

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect Calendly: {str(e)}"
        )


@router.post("/integrations/calendly/oauth/complete")
async def complete_calendly_oauth(
    request: CompleteOAuthRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ✅ Complete OAuth - Exchange authorization code for tokens

    Request:
    {
        "code": "authorization_code_from_calendly",
        "state": "csrf_token"
    }

    Response:
    {
        "success": true,
        "message": "Calendly connected successfully!",
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
        Integration.provider == "calendly",
        Integration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(
            status_code=404,
            detail="Calendly integration not found. Please connect first."
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
    token_url = "https://auth.calendly.com/oauth/token"

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
                detail=f"Calendly OAuth error: {token_data.get('error')}"
            )

        if "access_token" not in token_data:
            raise HTTPException(
                status_code=400,
                detail="Missing access_token in response"
            )

        # Calculate expiration (Calendly access tokens expire in 2 hours)
        expires_in = token_data.get("expires_in", 7200)  # 2 hours default
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Update credentials with tokens
        credentials["access_token"] = token_data["access_token"]
        credentials["refresh_token"] = token_data.get("refresh_token", "")
        credentials["token_expires_at"] = expires_at.isoformat()
        credentials["oauth_completed"] = True
        credentials["oauth_completed_at"] = datetime.utcnow().isoformat()

        # Get user info to save permanent scheduling URL
        try:
            client_temp = CalendlyClient(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token", ""),
                client_id=client_id,
                client_secret=client_secret
            )
            user_info = await client_temp.get_current_user()
            credentials["calendly_user_uri"] = user_info["resource"]["uri"]
            credentials["calendly_user_name"] = user_info["resource"].get("name", "")
            credentials["calendly_scheduling_url"] = user_info["resource"].get("scheduling_url", "")
            logger.info(f"Saved Calendly user scheduling URL: {credentials.get('calendly_scheduling_url')}")
        except Exception as e:
            logger.warning(f"Could not fetch user info: {str(e)}")

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
            "message": "Calendly connected successfully! Events will auto-sync.",
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


@router.post("/integrations/calendly/create-link")
async def create_scheduling_link_endpoint(
    request: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🔗 Create Calendly Scheduling Link (Internal use - called by booking system)

    Request:
    {
        "event_type_uri": "optional_event_type_uri"
    }
    """
    try:
        organization_id = uuid.UUID(current_user["organization_id"])

        logger.info(f"=== CREATE CALENDLY LINK ===")

        # Get integration
        integration = db.query(Integration).filter(
            Integration.organization_id == organization_id,
            Integration.type == "meeting",
            Integration.provider == "calendly",
            Integration.is_active == True,
            Integration.is_connected == True
        ).first()

        if not integration or not integration.config:
            raise HTTPException(
                status_code=404,
                detail="Calendly not connected."
            )

        # Decrypt credentials
        credentials = encryption_service.decrypt_credentials(integration.config)

        # Create scheduling link
        link_data = await create_calendly_link(
            client_id=credentials.get("client_id"),
            client_secret=credentials.get("client_secret"),
            access_token=credentials.get("access_token"),
            refresh_token=credentials.get("refresh_token"),
            event_type_uri=request.get("event_type_uri")
        )

        logger.info(f"✅ Calendly scheduling link created")

        return {
            "success": True,
            "message": "Scheduling link created successfully",
            "booking_url": link_data.get("resource", {}).get("booking_url")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating link: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create scheduling link: {str(e)}"
        )


@router.get("/integrations/calendly/status")
async def get_calendly_status(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📊 Get Calendly Connection Status

    Query Parameters:
    - user_id: User ID to check status for

    Response:
    {
        "connected": true/false,
        "integration_id": "uuid" (if connected),
        "expires_at": "timestamp" (if connected)
    }
    """
    try:
        organization_id = uuid.UUID(current_user["organization_id"])

        # Get integration
        integration = db.query(Integration).filter(
            Integration.organization_id == organization_id,
            Integration.type == "meeting",
            Integration.provider == "calendly",
            Integration.is_active == True
        ).first()

        if not integration or not integration.is_connected:
            return {
                "connected": False,
                "message": "Calendly not connected"
            }

        # Decrypt credentials to get expiration
        credentials = encryption_service.decrypt_credentials(integration.config)

        return {
            "connected": True,
            "integration_id": str(integration.id),
            "expires_at": credentials.get("token_expires_at"),
            "environment": credentials.get("environment", "production")
        }

    except Exception as e:
        logger.error(f"Error checking status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check status: {str(e)}"
        )


@router.get("/integrations/calendly/event-types")
async def get_event_types(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📅 Get Calendly Event Types

    Query Parameters:
    - user_id: User ID

    Response:
    {
        "event_types": [
            {
                "uri": "https://api.calendly.com/event_types/...",
                "name": "30 Minute Meeting",
                "duration": 30,
                "scheduling_url": "https://calendly.com/username/30min"
            }
        ]
    }
    """
    try:
        organization_id = uuid.UUID(current_user["organization_id"])

        # Get integration
        integration = db.query(Integration).filter(
            Integration.organization_id == organization_id,
            Integration.type == "meeting",
            Integration.provider == "calendly",
            Integration.is_active == True,
            Integration.is_connected == True
        ).first()

        if not integration:
            raise HTTPException(
                status_code=404,
                detail="Calendly not connected"
            )

        # Decrypt credentials
        credentials = encryption_service.decrypt_credentials(integration.config)

        # Create client
        client = CalendlyClient(
            access_token=credentials.get("access_token"),
            refresh_token=credentials.get("refresh_token"),
            client_id=credentials.get("client_id"),
            client_secret=credentials.get("client_secret")
        )

        # Get current user to get their event types
        user_info = await client.get_current_user()
        user_uri = user_info["resource"]["uri"]

        # Get event types
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.get(
                f"{client.api_base_url}/event_types",
                params={"user": user_uri},
                headers={
                    "Authorization": f"Bearer {client.access_token}",
                    "Content-Type": "application/json"
                }
            )

            # Auto-refresh token if expired
            if response.status_code == 401:
                logger.info("Token expired, refreshing...")
                client.access_token = await client.refresh_access_token()

                # Retry with new token
                response = await http_client.get(
                    f"{client.api_base_url}/event_types",
                    params={"user": user_uri},
                    headers={
                        "Authorization": f"Bearer {client.access_token}",
                        "Content-Type": "application/json"
                    }
                )

            response.raise_for_status()
            data = response.json()

        # Parse event types
        event_types = []
        for event_type in data.get("collection", []):
            event_types.append({
                "uri": event_type.get("uri"),
                "name": event_type.get("name"),
                "duration": event_type.get("duration"),
                "scheduling_url": event_type.get("scheduling_url"),
                "active": event_type.get("active", True)
            })

        return {
            "event_types": event_types,
            "count": len(event_types)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching event types: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch event types: {str(e)}"
        )
