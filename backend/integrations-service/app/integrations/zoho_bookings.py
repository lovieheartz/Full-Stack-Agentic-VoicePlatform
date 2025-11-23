"""
Zoho Bookings Integration with OAuth Flow + Zoom Meeting Creation
MCP Server calls these endpoints during the call to create bookings with Zoom links
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
import secrets
import httpx

from app.database import get_db
from app.models import Integration
from app.encryption import encryption_service
from app.security import get_current_user, get_current_user_flexible
from app.config import settings
from app.schemas import (
    IntegrationResponse,
    ZohoBookingsCredentialsRequest,
    CreateBookingRequest,
    BookingResponse,
    CompleteOAuthRequest
)
# Import Zoom meeting creation function
from app.integrations.zoom import create_zoom_meeting

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# ZOHO BOOKINGS CLIENT
# ============================================================================

class ZohoBookingsClient:
    """Client for Zoho Bookings API"""

    def __init__(self, access_token: str, refresh_token: str, client_id: str,
                 client_secret: str, api_domain: str, accounts_server: str, workspace_id: str = None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_domain = api_domain
        self.accounts_server = accounts_server
        self.workspace_id = workspace_id

    async def refresh_access_token(self) -> str:
        """Refresh expired access token"""
        token_url = f"https://{self.accounts_server}/oauth/v2/token"

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

    async def create_booking(
        self,
        service_id: str,
        customer_name: str,
        customer_email: str,
        customer_phone: str,
        booking_date: str,
        booking_time: str,
        duration_minutes: int = 30,
        staff_id: str = None,
        notes: str = None
    ) -> dict:
        """
        Create a booking in Zoho Bookings

        Args:
            service_id: Zoho service ID
            customer_name: Customer full name
            customer_email: Customer email
            customer_phone: Customer phone
            booking_date: Date in YYYY-MM-DD format
            booking_time: Time in HH:MM format (24-hour)
            duration_minutes: Duration in minutes
            staff_id: Optional staff member ID
            notes: Optional booking notes
        """
        # Combine date and time
        booking_datetime = datetime.strptime(f"{booking_date} {booking_time}", "%Y-%m-%d %H:%M")
        end_datetime = booking_datetime + timedelta(minutes=duration_minutes)

        # Build API URL (Correct Zoho Bookings API format)
        # Extract region from api_domain (e.g., bookings.zoho.in -> in)
        region = self.api_domain.split('.')[-1]
        base_url = f"https://www.zohoapis.{region}/bookings/v1/json"

        # According to official API docs, booking endpoint is /appointment (singular)
        booking_url = f"{base_url}/appointment"

        # Prepare booking data with correct Zoho API date format
        # Zoho requires: "dd-MMM-yyyy HH:mm:ss" format
        from_time_str = booking_datetime.strftime("%d-%b-%Y %H:%M:%S")
        to_time_str = end_datetime.strftime("%d-%b-%Y %H:%M:%S")

        # Zoho API requires customer_details as a stringified JSON (without extra encoding)
        import json
        customer_details_str = json.dumps({
            "name": customer_name,
            "email": customer_email,
            "phone_number": customer_phone
        }, separators=(',', ':'))  # Compact JSON without spaces

        booking_data = {
            "service_id": service_id,
            "customer_details": customer_details_str,
            "from_time": from_time_str,
            "to_time": to_time_str,
            "timezone": "Asia/Kolkata"
        }

        if staff_id:
            booking_data["staff_id"] = staff_id
        if notes:
            booking_data["notes"] = notes

        # Make API call - Zoho requires form-data, not JSON
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                booking_url,
                data=booking_data,  # Use 'data' for form-data instead of 'json'
                headers={
                    "Authorization": f"Zoho-oauthtoken {self.access_token}"
                    # Don't set Content-Type - httpx will set it to application/x-www-form-urlencoded
                }
            )

            # Auto-refresh token if expired
            if response.status_code == 401:
                logger.info("Token expired, refreshing...")
                self.access_token = await self.refresh_access_token()

                # Retry with new token
                response = await client.post(
                    booking_url,
                    json=booking_data,
                    headers={
                        "Authorization": f"Zoho-oauthtoken {self.access_token}",
                        "Content-Type": "application/json"
                    }
                )

            response.raise_for_status()
            result = response.json()
            return result


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/integrations/zoho-bookings/connect")
async def connect_zoho_bookings(
    request: ZohoBookingsCredentialsRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🚀 Connect Zoho Bookings - Initiate OAuth Flow

    Request:
    {
        "client_id": "1000.XXXX",
        "client_secret": "secret",
        "api_domain": "bookings.zoho.in",
        "workspace_id": "optional_workspace_id"
    }

    Response:
    {
        "success": true,
        "message": "Credentials saved. Please authorize.",
        "authorization_url": "https://accounts.zoho.in/oauth/v2/auth?...",
        "state": "csrf_token",
        "integration_id": "uuid",
        "provider": "zoho_bookings"
    }
    """
    try:
        organization_id = uuid.UUID(current_user["organization_id"])

        logger.info(f"=== CONNECT ZOHO BOOKINGS ===")
        logger.info(f"Organization: {organization_id}")
        logger.info(f"API Domain: {request.api_domain}")

        # Determine region from api_domain
        region = request.api_domain.split('.')[-1]  # Extract region (in, com, eu, etc.)
        accounts_server = f"accounts.zoho.{region}"
        api_domain = f"bookings.zoho.{region}"

        # Generate CSRF state token
        state = secrets.token_urlsafe(32)

        # Prepare encrypted credentials
        credentials_data = {
            "client_id": request.client_id,
            "client_secret": request.client_secret,
            "api_domain": api_domain,
            "accounts_server": accounts_server,
            "workspace_id": request.workspace_id,
            "oauth_state": state,
            "oauth_user_id": current_user.get("sub"),
            "oauth_initiated_at": datetime.utcnow().isoformat()
        }

        encrypted_config = encryption_service.encrypt_credentials(credentials_data)

        # Check if integration exists
        existing = db.query(Integration).filter(
            Integration.organization_id == organization_id,
            Integration.type == "meeting",
            Integration.provider == "zoho_bookings"
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
                name="Zoho Bookings",
                type="meeting",
                provider="zoho_bookings",
                config=encrypted_config,
                is_active=True,
                is_connected=False
            )
            db.add(new_integration)
            db.flush()
            integration_id = str(new_integration.id)
            logger.info(f"Created integration: {integration_id}")

        db.commit()

        # Build OAuth URL with correct Zoho Bookings scope
        redirect_uri = f"{settings.FRONTEND_URL}/oauth/callback"
        scope = "zohobookings.data.CREATE"  # Official Zoho Bookings API scope

        auth_url = (
            f"https://{accounts_server}/oauth/v2/auth"
            f"?scope={scope}"
            f"&client_id={request.client_id}"
            f"&response_type=code"
            f"&access_type=offline"
            f"&redirect_uri={redirect_uri}"
            f"&state={state}"
            f"&prompt=consent"
        )

        logger.info(f"✅ OAuth URL generated")

        return {
            "success": True,
            "message": "Zoho Bookings credentials saved. Please authorize in popup.",
            "authorization_url": auth_url,
            "state": state,
            "integration_id": integration_id,
            "provider": "zoho_bookings"
        }

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect Zoho Bookings: {str(e)}"
        )


@router.post("/integrations/zoho-bookings/oauth/complete")
async def complete_zoho_bookings_oauth(
    request: CompleteOAuthRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ✅ Complete OAuth - Exchange authorization code for tokens

    Request:
    {
        "code": "authorization_code_from_zoho",
        "state": "csrf_token"
    }

    Response:
    {
        "success": true,
        "message": "Zoho Bookings connected successfully!",
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
        Integration.provider == "zoho_bookings",
        Integration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(
            status_code=404,
            detail="Zoho Bookings integration not found. Please connect first."
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
    accounts_server = credentials.get("accounts_server", "accounts.zoho.com")

    # Exchange code for tokens
    redirect_uri = f"{settings.FRONTEND_URL}/oauth/callback"
    token_url = f"https://{accounts_server}/oauth/v2/token"

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
                detail=f"Zoho OAuth error: {token_data.get('error')}"
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
            "message": "Zoho Bookings connected successfully! You can now create bookings.",
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


@router.post("/integrations/zoho-bookings/save-config")
async def save_zoho_bookings_config(
    request: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    💾 Save Service and Staff IDs (from frontend form)

    Request:
    {
        "service_id": "353508000000042050",
        "staff_id": "353508000000042014"
    }
    """
    logger.info(f"=== SAVE CONFIG ===")

    # Get integration
    integration = db.query(Integration).filter(
        Integration.organization_id == uuid.UUID(current_user["organization_id"]),
        Integration.type == "meeting",
        Integration.provider == "zoho_bookings",
        Integration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(
            status_code=404,
            detail="Zoho Bookings integration not found."
        )

    # Decrypt, update, and re-encrypt credentials
    credentials = encryption_service.decrypt_credentials(integration.config)
    credentials["service_id"] = request.get("service_id")
    credentials["staff_id"] = request.get("staff_id")

    integration.config = encryption_service.encrypt_credentials(credentials)
    db.commit()

    logger.info(f"✅ Config saved")

    return {
        "success": True,
        "message": "Configuration saved successfully"
    }


@router.post("/integrations/zoho-bookings/test-booking", response_model=BookingResponse)
async def test_booking(
    request: CreateBookingRequest,
    current_user: dict = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """
    🧪 TEST ENDPOINT - Create a mock booking to test the flow without OAuth
    This endpoint simulates Zoho Bookings working properly
    """
    try:
        logger.info(f"=== TEST BOOKING (MOCK) ===")
        logger.info(f"Customer: {request.customer_name}")
        logger.info(f"Date: {request.booking_date}, Time: {request.booking_time}")

        # Simulate successful booking
        mock_booking_id = f"TEST-{uuid.uuid4().hex[:8]}"

        return BookingResponse(
            success=True,
            message="TEST: Booking created successfully (simulated - not in real Zoho)",
            booking_id=mock_booking_id,
            booking_link=f"https://bookings.zoho.in/portal/test-booking/{mock_booking_id}",
            customer_name=request.customer_name,
            booking_date=request.booking_date,
            booking_time=request.booking_time,
            duration_minutes=request.duration_minutes
        )
    except Exception as e:
        logger.error(f"Test booking error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/integrations/zoho-bookings/create-booking", response_model=BookingResponse)
async def create_booking(
    request: CreateBookingRequest,
    current_user: dict = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    """
    📅 Create Booking in Zoho Bookings (Called by MCP Server during call)

    Request:
    {
        "service_id": "1234567890",
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "customer_phone": "+919876543210",
        "booking_date": "2025-12-25",
        "booking_time": "14:30",
        "duration_minutes": 60,
        "staff_id": "optional_staff_id",
        "notes": "Scheduled during AI call"
    }
    """
    try:
        organization_id = uuid.UUID(current_user["organization_id"])

        logger.info(f"=== CREATE BOOKING ===")
        logger.info(f"Service: {request.service_id}, Customer: {request.customer_name}")
        logger.info(f"Date: {request.booking_date}, Time: {request.booking_time}")

        # Get integration
        integration = db.query(Integration).filter(
            Integration.organization_id == organization_id,
            Integration.type == "meeting",
            Integration.provider == "zoho_bookings",
            Integration.is_active == True,
            Integration.is_connected == True
        ).first()

        if not integration or not integration.config:
            raise HTTPException(
                status_code=404,
                detail="Zoho Bookings not connected. Please connect first."
            )

        # Decrypt credentials
        credentials = encryption_service.decrypt_credentials(integration.config)

        # Get service_id and staff_id from request or use saved defaults
        service_id = request.service_id or credentials.get("service_id")
        staff_id = request.staff_id or credentials.get("staff_id")

        if not service_id:
            raise HTTPException(
                status_code=400,
                detail="service_id is required. Please configure it in admin settings."
            )

        if not staff_id:
            raise HTTPException(
                status_code=400,
                detail="staff_id is required. Please configure it in admin settings."
            )

        logger.info(f"Using service_id: {service_id}, staff_id: {staff_id}")

        # Step 1: Create Zoom meeting and include link in booking notes
        zoom_meeting_link = None
        zoom_password = None
        zoom_meeting_id = None

        try:
            # Get Zoom credentials from integrations table
            zoom_integration = db.query(Integration).filter(
                Integration.organization_id == organization_id,
                Integration.type == "meeting",
                Integration.provider == "zoom",
                Integration.is_active == True
            ).first()

            if zoom_integration and zoom_integration.config:
                logger.info("🎥 Creating Zoom meeting in Asia/Kolkata timezone...")

                # Decrypt Zoom credentials
                zoom_credentials = encryption_service.decrypt_credentials(zoom_integration.config)

                # Format booking datetime for Zoom (Asia/Kolkata timezone)
                booking_datetime = datetime.strptime(f"{request.booking_date} {request.booking_time}", "%Y-%m-%d %H:%M")
                zoom_start_time = booking_datetime.strftime("%Y-%m-%dT%H:%M:%S")

                # Create Zoom meeting with Asia/Kolkata timezone to match Zoho Bookings
                zoom_meeting = await create_zoom_meeting(
                    account_id=zoom_credentials["account_id"],
                    client_id=zoom_credentials["client_id"],
                    client_secret=zoom_credentials["client_secret"],
                    topic=f"Meeting with {request.customer_name}",
                    start_time=zoom_start_time,
                    duration=request.duration_minutes,
                    timezone="Asia/Kolkata",
                    agenda=request.notes or f"Scheduled meeting with {request.customer_name}"
                )

                zoom_meeting_link = zoom_meeting.get("join_url")
                zoom_password = zoom_meeting.get("password")
                zoom_meeting_id = zoom_meeting.get("meeting_id")

                logger.info(f"✅ Zoom meeting created: {zoom_meeting_id}")
            else:
                logger.info("⚠️ Zoom integration not found - booking without Zoom link")

        except Exception as zoom_error:
            logger.error(f"⚠️ Failed to create Zoom meeting: {str(zoom_error)}")
            logger.info("Continuing with booking without Zoom link")

        # Step 2: Prepare booking notes with Zoom link
        booking_notes = request.notes or ""
        if zoom_meeting_link:
            booking_notes += f"\n\n🎥 Zoom Meeting Link: {zoom_meeting_link}"
            if zoom_password:
                booking_notes += f"\n🔐 Password: {zoom_password}"
            booking_notes += f"\n📍 Meeting ID: {zoom_meeting_id}"

        # Step 2.5: Sync to connected calendars (Google Calendar, Calendly)
        calendar_links = []

        try:
            # Google Calendar sync
            google_cal_integration = db.query(Integration).filter(
                Integration.organization_id == organization_id,
                Integration.type == "meeting",
                Integration.provider == "google_calendar",
                Integration.is_active == True,
                Integration.is_connected == True
            ).first()

            if google_cal_integration and google_cal_integration.config:
                logger.info("📅 Creating Google Calendar event...")

                # Import Google Calendar helper
                from app.integrations.google_calendar import create_google_calendar_event

                # Decrypt Google Calendar credentials
                google_cal_credentials = encryption_service.decrypt_credentials(google_cal_integration.config)

                # Parse booking datetime
                booking_datetime = datetime.strptime(f"{request.booking_date} {request.booking_time}", "%Y-%m-%d %H:%M")
                end_datetime = booking_datetime + timedelta(minutes=request.duration_minutes)

                # Create Google Calendar event with Google Meet link
                google_event = await create_google_calendar_event(
                    client_id=google_cal_credentials.get("client_id"),
                    client_secret=google_cal_credentials.get("client_secret"),
                    access_token=google_cal_credentials.get("access_token"),
                    refresh_token=google_cal_credentials.get("refresh_token"),
                    summary=f"Meeting with {request.customer_name}",
                    description=request.notes or f"Scheduled meeting with {request.customer_name}",
                    start_time=booking_datetime,
                    end_time=end_datetime,
                    attendee_email=request.customer_email,
                    add_google_meet=True,
                    timezone="Asia/Kolkata"
                )

                # Extract links from Google Calendar event
                event_link = google_event.get("htmlLink")
                meet_link = google_event.get("hangoutLink")

                if event_link:
                    calendar_links.append(f"📅 Google Calendar: {event_link}")
                if meet_link:
                    calendar_links.append(f"🎥 Google Meet: {meet_link}")

                logger.info(f"✅ Google Calendar event created: {google_event.get('id')}")
            else:
                logger.info("⚠️ Google Calendar not connected - skipping calendar sync")

        except Exception as google_cal_error:
            logger.error(f"⚠️ Failed to create Google Calendar event: {str(google_cal_error)}")
            logger.info("Continuing with booking without Google Calendar sync")

        try:
            # Calendly sync
            calendly_integration = db.query(Integration).filter(
                Integration.organization_id == organization_id,
                Integration.type == "meeting",
                Integration.provider == "calendly",
                Integration.is_active == True,
                Integration.is_connected == True
            ).first()

            if calendly_integration and calendly_integration.config:
                logger.info("🗓️ Creating Calendly scheduling link...")

                # Import Calendly helper
                from app.integrations.calendly import create_calendly_link

                # Decrypt Calendly credentials
                calendly_credentials = encryption_service.decrypt_credentials(calendly_integration.config)

                # Create Calendly scheduling link
                # Note: event_type_uri should be configured in Calendly setup
                calendly_link = await create_calendly_link(
                    client_id=calendly_credentials.get("client_id"),
                    client_secret=calendly_credentials.get("client_secret"),
                    access_token=calendly_credentials.get("access_token"),
                    refresh_token=calendly_credentials.get("refresh_token"),
                    event_type_uri=calendly_credentials.get("event_type_uri")
                )

                # Extract booking URL from Calendly response
                booking_url = calendly_link.get("resource", {}).get("booking_url")

                if booking_url:
                    calendar_links.append(f"🗓️ Calendly: {booking_url}")

                logger.info(f"✅ Calendly scheduling link created")
            else:
                logger.info("⚠️ Calendly not connected - skipping Calendly sync")

        except Exception as calendly_error:
            logger.error(f"⚠️ Failed to create Calendly link: {str(calendly_error)}")
            logger.info("Continuing with booking without Calendly sync")

        # Append calendar links to booking notes
        if calendar_links:
            booking_notes += "\n\n📅 Calendar Links:\n" + "\n".join(calendar_links)

        # Step 3: Create Zoho Bookings client
        zoho_client = ZohoBookingsClient(
            access_token=credentials.get("access_token"),
            refresh_token=credentials.get("refresh_token"),
            client_id=credentials.get("client_id"),
            client_secret=credentials.get("client_secret"),
            api_domain=credentials.get("api_domain"),
            accounts_server=credentials.get("accounts_server"),
            workspace_id=credentials.get("workspace_id")
        )

        # Step 4: Create booking with Zoom link in notes
        booking_result = await zoho_client.create_booking(
            service_id=service_id,
            customer_name=request.customer_name,
            customer_email=request.customer_email,
            customer_phone=request.customer_phone,
            booking_date=request.booking_date,
            booking_time=request.booking_time,
            duration_minutes=request.duration_minutes,
            staff_id=staff_id,
            notes=booking_notes.strip()
        )

        # Update access token if refreshed
        if zoho_client.access_token != credentials.get("access_token"):
            credentials["access_token"] = zoho_client.access_token
            credentials["token_expires_at"] = (datetime.utcnow() + timedelta(hours=1)).isoformat()
            integration.config = encryption_service.encrypt_credentials(credentials)
            db.commit()

        logger.info(f"✅ Booking created successfully")

        # Prepare success message
        success_message = "Booking created successfully in Zoho Bookings"
        if zoom_meeting_link:
            success_message += f" with Zoom meeting link"

        return BookingResponse(
            success=True,
            message=success_message,
            booking_id=booking_result.get("booking_id"),
            booking_link=booking_result.get("booking_link"),
            customer_name=request.customer_name,
            booking_date=request.booking_date,
            booking_time=request.booking_time,
            duration_minutes=request.duration_minutes
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Invalid date/time format: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date/time format: {str(e)}"
        )
    except httpx.HTTPStatusError as e:
        error_detail = e.response.json() if e.response else str(e)
        logger.error(f"Zoho API error: {error_detail}")
        raise HTTPException(
            status_code=e.response.status_code if e.response else 500,
            detail=f"Failed to create booking: {error_detail}"
        )
    except Exception as e:
        logger.error(f"Error creating booking: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create booking: {str(e)}"
        )
