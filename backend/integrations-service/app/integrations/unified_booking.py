"""
Unified Meeting Booking System
Works with ANY combination of integrations: Zoom, Google Calendar, Calendly, Zoho Bookings
Completely modular - each integration is optional and independent
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
import httpx
from typing import Optional

from app.database import get_db
from app.models import Integration
from app.encryption import encryption_service
from app.security import get_current_user
from app.integrations.zoom import create_zoom_meeting
from app.integrations.google_calendar import create_google_calendar_event

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/integrations/book-meeting")
async def book_meeting(
    request: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📅 Unified Meeting Booking Endpoint

    Works with ANY combination of:
    - Zoom (creates video meeting)
    - Google Calendar (creates calendar event with Google Meet link)
    - Calendly (creates scheduling link)
    - Zoho Bookings (creates appointment)

    If NO integrations connected, returns error
    If ANY integration connected, creates meeting and returns links

    Request:
    {
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "customer_phone": "+919876543210",  # Optional
        "booking_date": "2025-12-25",  # YYYY-MM-DD
        "booking_time": "14:30",  # HH:MM (24-hour)
        "duration_minutes": 30,
        "notes": "Optional meeting notes",
        "timezone": "Asia/Kolkata"  # Optional, defaults to Asia/Kolkata
    }

    Response:
    {
        "success": true,
        "message": "Meeting booked successfully!",
        "meeting_details": {
            "customer_name": "John Doe",
            "booking_date": "2025-12-25",
            "booking_time": "14:30",
            "duration_minutes": 30,
            "timezone": "Asia/Kolkata"
        },
        "zoom_meeting": {
            "join_url": "https://zoom.us/j/123456789",
            "meeting_id": "123 456 789",
            "password": "abc123"
        },  # Only if Zoom connected
        "google_calendar": {
            "event_link": "https://calendar.google.com/...",
            "google_meet_link": "https://meet.google.com/..."
        },  # Only if Google Calendar connected
        "calendly": {
            "scheduling_link": "https://calendly.com/..."
        },  # Only if Calendly connected
        "zoho_bookings": {
            "booking_id": "12345",
            "booking_link": "https://..."
        }  # Only if Zoho Bookings connected
    }
    """
    try:
        organization_id = uuid.UUID(current_user["organization_id"])

        logger.info(f"=== UNIFIED MEETING BOOKING ===")
        logger.info(f"Customer: {request.get('customer_name')}")
        logger.info(f"Date: {request.get('booking_date')}, Time: {request.get('booking_time')}")

        # Parse datetime
        customer_name = request.get("customer_name")
        customer_email = request.get("customer_email")
        customer_phone = request.get("customer_phone", "")
        booking_date = request.get("booking_date")
        booking_time = request.get("booking_time")
        duration_minutes = request.get("duration_minutes", 30)
        notes = request.get("notes", "")
        timezone = request.get("timezone", "Asia/Kolkata")

        # Validate required fields
        if not all([customer_name, customer_email, booking_date, booking_time]):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: customer_name, customer_email, booking_date, booking_time"
            )

        # Parse booking datetime
        booking_datetime = datetime.strptime(f"{booking_date} {booking_time}", "%Y-%m-%d %H:%M")
        end_datetime = booking_datetime + timedelta(minutes=duration_minutes)

        # Response object
        response = {
            "success": True,
            "message": "Meeting booked successfully!",
            "meeting_details": {
                "customer_name": customer_name,
                "customer_email": customer_email,
                "booking_date": booking_date,
                "booking_time": booking_time,
                "duration_minutes": duration_minutes,
                "timezone": timezone
            }
        }

        # Track which integrations worked
        integrations_used = []
        all_meeting_links = []
        integration_errors = {}  # Track errors for debugging

        # ==============================================================
        # ZOOM INTEGRATION (Optional)
        # ==============================================================
        try:
            zoom_integration = db.query(Integration).filter(
                Integration.organization_id == organization_id,
                Integration.type == "meeting",
                Integration.provider == "zoom",
                Integration.is_active == True,
                Integration.is_connected == True
            ).first()

            if zoom_integration and zoom_integration.config:
                logger.info("🎥 Creating Zoom meeting...")

                zoom_credentials = encryption_service.decrypt_credentials(zoom_integration.config)
                zoom_start_time = booking_datetime.strftime("%Y-%m-%dT%H:%M:%S")

                zoom_meeting = await create_zoom_meeting(
                    account_id=zoom_credentials["account_id"],
                    client_id=zoom_credentials["client_id"],
                    client_secret=zoom_credentials["client_secret"],
                    topic=f"Meeting with {customer_name}",
                    start_time=zoom_start_time,
                    duration=duration_minutes,
                    timezone=timezone,
                    agenda=notes or f"Scheduled meeting with {customer_name}"
                )

                response["zoom_meeting"] = {
                    "join_url": zoom_meeting.get("join_url"),
                    "meeting_id": zoom_meeting.get("meeting_id"),
                    "password": zoom_meeting.get("password")
                }

                integrations_used.append("Zoom")
                all_meeting_links.append(f"🎥 Zoom: {zoom_meeting.get('join_url')}")
                if zoom_meeting.get("password"):
                    all_meeting_links.append(f"🔐 Password: {zoom_meeting.get('password')}")

                logger.info(f"✅ Zoom meeting created: {zoom_meeting.get('meeting_id')}")

        except Exception as zoom_error:
            logger.warning(f"⚠️ Zoom failed: {str(zoom_error)}")
            # Continue with other integrations

        # ==============================================================
        # GOOGLE CALENDAR INTEGRATION (Optional)
        # ==============================================================
        try:
            google_cal_integration = db.query(Integration).filter(
                Integration.organization_id == organization_id,
                Integration.type == "meeting",
                Integration.provider == "google_calendar",
                Integration.is_active == True,
                Integration.is_connected == True
            ).first()

            if google_cal_integration and google_cal_integration.config:
                logger.info("📅 Creating Google Calendar event...")

                google_cal_credentials = encryption_service.decrypt_credentials(google_cal_integration.config)

                google_event = await create_google_calendar_event(
                    client_id=google_cal_credentials.get("client_id"),
                    client_secret=google_cal_credentials.get("client_secret"),
                    access_token=google_cal_credentials.get("access_token"),
                    refresh_token=google_cal_credentials.get("refresh_token"),
                    summary=f"Meeting with {customer_name}",
                    description=notes or f"Scheduled meeting with {customer_name}",
                    start_time=booking_datetime,
                    end_time=end_datetime,
                    attendee_email=customer_email,
                    add_google_meet=True,
                    timezone=timezone
                )

                response["google_calendar"] = {
                    "event_link": google_event.get("htmlLink"),
                    "google_meet_link": google_event.get("hangoutLink")
                }

                integrations_used.append("Google Calendar")
                if google_event.get("htmlLink"):
                    all_meeting_links.append(f"📅 Calendar: {google_event.get('htmlLink')}")
                if google_event.get("hangoutLink"):
                    all_meeting_links.append(f"🎥 Google Meet: {google_event.get('hangoutLink')}")

                logger.info(f"✅ Google Calendar event created: {google_event.get('id')}")

        except Exception as google_error:
            logger.warning(f"⚠️ Google Calendar failed: {str(google_error)}")
            # Continue with other integrations

        # ==============================================================
        # CALENDLY INTEGRATION (Optional)
        # ==============================================================
        try:
            calendly_integration = db.query(Integration).filter(
                Integration.organization_id == organization_id,
                Integration.type == "meeting",
                Integration.provider == "calendly",
                Integration.is_active == True,
                Integration.is_connected == True
            ).first()

            if calendly_integration and calendly_integration.config:
                logger.info("🗓️ Getting Calendly scheduling link...")

                calendly_credentials = encryption_service.decrypt_credentials(calendly_integration.config)

                # ALWAYS provide the permanent Calendly scheduling URL as fallback
                permanent_scheduling_url = calendly_credentials.get("calendly_scheduling_url")

                if permanent_scheduling_url:
                    # We have the permanent link - use it
                    response["calendly"] = {
                        "scheduling_link": permanent_scheduling_url,
                        "user_name": calendly_credentials.get("calendly_user_name", ""),
                        "status": "permanent_link_provided",
                        "note": "Use this link to schedule a meeting at your convenience"
                    }

                    integrations_used.append("Calendly")
                    all_meeting_links.append(f"🗓️ Calendly: {permanent_scheduling_url}")

                    logger.info(f"✅ Calendly permanent scheduling link provided: {permanent_scheduling_url}")
                else:
                    # Try to get event types to provide a link
                    try:
                        from app.integrations.calendly import CalendlyClient

                        client = CalendlyClient(
                            access_token=calendly_credentials.get("access_token"),
                            refresh_token=calendly_credentials.get("refresh_token"),
                            client_id=calendly_credentials.get("client_id"),
                            client_secret=calendly_credentials.get("client_secret")
                        )

                        # Get user's event types
                        user_info = await client.get_current_user()
                        user_uri = user_info["resource"]["uri"]

                        async with httpx.AsyncClient(timeout=30.0) as http_client:
                            response_cal = await http_client.get(
                                f"{client.api_base_url}/event_types",
                                params={"user": user_uri},
                                headers={
                                    "Authorization": f"Bearer {client.access_token}",
                                    "Content-Type": "application/json"
                                }
                            )
                            response_cal.raise_for_status()
                            event_types = response_cal.json().get("collection", [])

                            # Find appropriate event type based on duration
                            selected_event_type = None
                            for et in event_types:
                                if et.get("active", True):
                                    et_duration = et.get("duration", 30)
                                    # Try to match duration, or use first active event type
                                    if et_duration == duration_minutes or selected_event_type is None:
                                        selected_event_type = et
                                        if et_duration == duration_minutes:
                                            break  # Perfect match found

                            if selected_event_type:
                                response["calendly"] = {
                                    "scheduling_link": selected_event_type.get("scheduling_url"),
                                    "event_type_name": selected_event_type.get("name"),
                                    "duration": selected_event_type.get("duration"),
                                    "status": "event_type_link_provided"
                                }

                                integrations_used.append("Calendly")
                                all_meeting_links.append(f"🗓️ Calendly: {selected_event_type.get('scheduling_url')}")

                                logger.info(f"✅ Calendly scheduling link provided: {selected_event_type.get('name')}")

                    except Exception as api_error:
                        logger.warning(f"Could not fetch Calendly event types: {str(api_error)}")
                        # Don't add to response if we can't get a link
                        pass

        except Exception as calendly_error:
            error_msg = str(calendly_error)
            logger.error(f"❌ Calendly failed: {error_msg}", exc_info=True)
            integration_errors["calendly"] = error_msg
            # Continue with other integrations

        # ==============================================================
        # ZOHO BOOKINGS INTEGRATION (Optional)
        # ==============================================================
        try:
            zoho_integration = db.query(Integration).filter(
                Integration.organization_id == organization_id,
                Integration.type == "meeting",
                Integration.provider == "zoho_bookings",
                Integration.is_active == True,
                Integration.is_connected == True
            ).first()

            if zoho_integration and zoho_integration.config:
                logger.info("📅 Creating Zoho Bookings appointment...")

                zoho_credentials = encryption_service.decrypt_credentials(zoho_integration.config)

                # Call Zoho Bookings API
                from app.integrations.zoho_bookings import ZohoBookingsClient

                zoho_client = ZohoBookingsClient(
                    access_token=zoho_credentials.get("access_token"),
                    refresh_token=zoho_credentials.get("refresh_token"),
                    client_id=zoho_credentials.get("client_id"),
                    client_secret=zoho_credentials.get("client_secret"),
                    api_domain=zoho_credentials.get("api_domain"),
                    accounts_server=zoho_credentials.get("accounts_server"),
                    workspace_id=zoho_credentials.get("workspace_id")
                )

                # Get service_id and staff_id from credentials
                service_id = zoho_credentials.get("service_id")
                staff_id = zoho_credentials.get("staff_id")

                if not service_id or not staff_id:
                    logger.warning("⚠️ Zoho Bookings: service_id or staff_id not configured")
                    raise Exception("Zoho Bookings service_id and staff_id must be configured")

                # Create booking
                zoho_booking = await zoho_client.create_booking(
                    service_id=service_id,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone or "+000000000000",
                    booking_date=booking_date,
                    booking_time=booking_time,
                    duration_minutes=duration_minutes,
                    staff_id=staff_id,
                    notes=notes
                )

                response["zoho_bookings"] = {
                    "booking_id": zoho_booking.get("booking_id"),
                    "booking_link": zoho_booking.get("booking_link"),
                    "status": "booking_created"
                }

                integrations_used.append("Zoho Bookings")
                if zoho_booking.get("booking_link"):
                    all_meeting_links.append(f"📅 Zoho: {zoho_booking.get('booking_link')}")

                logger.info(f"✅ Zoho Bookings appointment created: {zoho_booking.get('booking_id')}")

        except Exception as zoho_error:
            error_msg = str(zoho_error)
            logger.error(f"❌ Zoho Bookings failed: {error_msg}", exc_info=True)
            integration_errors["zoho_bookings"] = error_msg
            # Continue with other integrations

        # ==============================================================
        # FINAL VALIDATION
        # ==============================================================
        if not integrations_used:
            raise HTTPException(
                status_code=404,
                detail="No meeting integrations are connected. Please connect at least one integration (Zoom, Google Calendar, Calendly, or Zoho Bookings) in the admin panel."
            )

        # ==============================================================
        # EMAIL CONFIRMATION (REQUIRED - Always send email with meeting details)
        # ==============================================================
        try:
            logger.info(f"📧 Sending confirmation email to {customer_email}...")

            # Get Gmail integration
            gmail_integration = db.query(Integration).filter(
                Integration.organization_id == organization_id,
                Integration.type == "email",
                Integration.provider == "gmail",
                Integration.is_active == True,
                Integration.is_connected == True
            ).first()

            if gmail_integration and gmail_integration.config:
                from app.integrations.gmail import send_gmail_email

                gmail_credentials = encryption_service.decrypt_credentials(gmail_integration.config)

                # Build email body with all meeting details
                email_subject = f"Meeting Confirmation - {booking_date} at {booking_time}"

                email_body = f"""Dear {customer_name},

Your meeting has been successfully scheduled!

Meeting Details:
================================
Date: {booking_date}
Time: {booking_time} ({timezone})
Duration: {duration_minutes} minutes
"""

                # Add Zoom details if available
                if "zoom_meeting" in response:
                    zoom = response["zoom_meeting"]
                    email_body += f"""
Zoom Meeting Details:
================================
Join URL: {zoom.get('join_url')}
Meeting ID: {zoom.get('meeting_id')}
"""
                    if zoom.get('password'):
                        email_body += f"Password: {zoom.get('password')}\n"

                # Add Google Calendar/Meet details if available
                if "google_calendar" in response:
                    gcal = response["google_calendar"]
                    email_body += f"""
Google Calendar Event:
================================
"""
                    if gcal.get('event_link'):
                        email_body += f"Calendar Event: {gcal.get('event_link')}\n"
                    if gcal.get('google_meet_link'):
                        email_body += f"Google Meet: {gcal.get('google_meet_link')}\n"

                # Add Calendly details if available
                if "calendly" in response:
                    calendly = response["calendly"]
                    if calendly.get('scheduling_link'):
                        email_body += f"""
Calendly Scheduling Link:
================================
Scheduling URL: {calendly.get('scheduling_link')}
"""
                    if calendly.get('booking_url'):
                        email_body += f"""
Calendly Booking Link:
================================
Booking URL: {calendly.get('booking_url')}
"""

                # Add Zoho Bookings details if available
                if "zoho_bookings" in response:
                    zoho = response["zoho_bookings"]
                    if zoho.get('booking_id'):
                        email_body += f"""
Zoho Bookings:
================================
Booking ID: {zoho.get('booking_id')}
"""
                    if zoho.get('booking_link'):
                        email_body += f"Booking Link: {zoho.get('booking_link')}\n"

                # Add notes if available
                if notes:
                    email_body += f"""
Additional Notes:
================================
{notes}
"""

                email_body += """

If you have any questions or need to reschedule, please contact us.

Best regards,
Your Team

================================
This is an automated confirmation email.
"""

                # Send email
                send_gmail_email(
                    email=gmail_credentials.get("email"),
                    app_password=gmail_credentials.get("app_password"),
                    to_email=customer_email,
                    subject=email_subject,
                    body=email_body
                )

                logger.info(f"✅ Confirmation email sent to {customer_email}")
                response["email_sent"] = True

            else:
                logger.warning("⚠️ Gmail not connected - skipping confirmation email")
                response["email_sent"] = False
                response["message"] += " (Note: Email confirmation not sent - Gmail not connected)"

        except Exception as email_error:
            logger.error(f"⚠️ Failed to send confirmation email: {str(email_error)}")
            response["email_sent"] = False
            # Don't fail the whole booking if email fails - meeting is already created

        # Update response message
        response["message"] = f"Meeting booked successfully via {', '.join(integrations_used)}!"
        if response.get("email_sent"):
            response["message"] += f" Confirmation email sent to {customer_email}."
        response["integrations_used"] = integrations_used
        
        # Add error details for debugging
        if integration_errors:
            response["integration_errors"] = integration_errors

        logger.info(f"✅ Meeting booked successfully via: {', '.join(integrations_used)}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error booking meeting: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to book meeting: {str(e)}"
        )
