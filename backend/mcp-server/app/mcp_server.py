import logging
import json
from typing import Any
from contextvars import ContextVar
import httpx
from mcp.server import Server
from mcp.types import Tool, TextContent
from app.config import settings

logger = logging.getLogger(__name__)

# Context variable to store JWT token or organization_id per-request
jwt_token_var: ContextVar[str] = ContextVar("jwt_token", default=None)


def set_jwt_token(token: str):
    """Store JWT token or organization_id in context for current request"""
    jwt_token_var.set(token)


def get_jwt_token() -> str:
    """Retrieve JWT token or organization_id from context"""
    return jwt_token_var.get()


def get_auth_headers() -> dict:
    """Get authentication headers for integration service requests

    Returns appropriate headers based on auth method:
    - JWT token: {"Authorization": "Bearer <token>"}
    - Organization ID: {"X-Organization-ID": "<org_id>"}
    """
    auth_value = get_jwt_token()
    if not auth_value:
        return {}

    # Check if it's a JWT token (contains dots) or organization_id (UUID format)
    if "." in auth_value:
        # JWT token
        return {"Authorization": f"Bearer {auth_value}"}
    else:
        # Organization ID
        return {"X-Organization-ID": auth_value}


# MCP Server instance
mcp_server = Server("alsatalk-integrations")


@mcp_server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Return all available MCP tools"""
    return [
        Tool(
            name="list_available_integrations",
            description="List all connected integrations available for use. CRITICAL: Call this tool FIRST before attempting any integration-specific actions (sending SMS, email, creating meetings, booking appointments). This tells you which integrations are connected and ready to use.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="send_sms",
            description="Send an SMS message to a phone number. CRITICAL: Only call this tool AFTER explicitly verifying the phone number with the customer by reading it back to them. Use this when the customer asks you to send them information via text message or SMS.",
            inputSchema={
                "type": "object",
                "properties": {
                    "phone_number": {"type": "string", "description": "Recipient phone number with country code in E.164 format (e.g., +12025551234, +919876543210). Must be verified with customer before sending. Always include country code."},
                    "message": {"type": "string", "description": "SMS message content to send to the customer. Keep under 140 characters if possible. If longer than 160 characters, message will be split into multiple SMS. If sending meeting link+password and total > 140 chars, send link and password separately."}
                },
                "required": ["phone_number", "message"]
            }
        ),
        Tool(
            name="send_email",
            description="Send an email to a recipient. CRITICAL: Only call this tool AFTER explicitly verifying the email address with the customer by spelling it back character by character. Use this when the customer asks you to send them information via email.",
            inputSchema={
                "type": "object",
                "properties": {
                    "to_email": {"type": "string", "description": "Recipient email address in valid format (user@domain.com). Must be verified with customer before sending. Must contain @ symbol and domain extension (.com, .org, etc.). Check for obvious errors before sending."},
                    "subject": {"type": "string", "description": "Email subject line (keep concise, 40-60 characters recommended). Should clearly describe email content."},
                    "body": {"type": "string", "description": "Email body content (plain text). Include all relevant details the customer needs."},
                    "html_body": {"type": "string", "description": "Optional HTML email body for formatted content. Use only if you have HTML content to send."}
                },
                "required": ["to_email", "subject", "body"]
            }
        ),
        Tool(
            name="create_zoom_meeting",
            description="Create a video meeting and return the meeting link. Use this when the customer asks to schedule a video meeting or wants a meeting link. You must convert natural language dates/times to ISO 8601 format before calling this tool.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Meeting title/topic as described by the customer. Keep it clear and professional."},
                    "start_time": {"type": "string", "description": "Meeting start time in ISO 8601 format: YYYY-MM-DDTHH:MM:SS (e.g., '2024-11-19T17:00:00' for Nov 19, 2024 at 5:00 PM). YOU must convert natural language (like 'tomorrow at 5pm') to this format. Use 24-hour format. Do NOT include 'Z' suffix unless time is in UTC."},
                    "duration": {"type": "integer", "description": "Meeting duration in minutes. Default is 60 minutes if customer doesn't specify. Common values: 30, 60, 90, 120."},
                    "timezone": {"type": "string", "description": "IANA timezone name (REQUIRED). Examples: 'America/New_York' (EST/EDT), 'America/Los_Angeles' (PST/PDT), 'America/Chicago' (CST/CDT), 'Asia/Kolkata' (IST), 'Europe/London' (GMT/BST), 'Asia/Tokyo' (JST), 'UTC'. Ask customer for timezone if not provided. Convert common abbreviations: EST→America/New_York, PST→America/Los_Angeles, IST→Asia/Kolkata, GMT→Europe/London."},
                    "agenda": {"type": "string", "description": "Optional meeting agenda or description. Include if customer provides specific topics to discuss."}
                },
                "required": ["topic", "start_time", "timezone"]
            }
        ),
        Tool(
            name="book_meeting",
            description="Book a meeting using ANY available integration (Zoom, Google Calendar, Calendly, Zoho Bookings). ONLY ask for: name, email, date, time. That's it - keep it simple! Works with whatever integrations are connected. Creates Zoom links, Google Calendar events with Meet, Calendly links, or Zoho appointments automatically.",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Customer name"},
                    "customer_email": {"type": "string", "description": "Customer email"},
                    "customer_phone": {"type": "string", "description": "Customer phone with country code (e.g., +919876543210). Optional - auto-filled if available."},
                    "booking_date": {"type": "string", "description": "Date in YYYY-MM-DD format (e.g., '2025-11-26'). Convert 'tomorrow' to actual date."},
                    "booking_time": {"type": "string", "description": "Time in HH:MM 24-hour format (e.g., '14:30' for 2:30 PM). Convert 12-hour to 24-hour."},
                    "duration_minutes": {"type": "integer", "description": "Duration in minutes. Default: 30"},
                    "notes": {"type": "string", "description": "Optional notes"},
                    "timezone": {"type": "string", "description": "Optional timezone. Default: Asia/Kolkata"}
                },
                "required": ["customer_name", "customer_email", "booking_date", "booking_time"]
            }
        ),
        Tool(
            name="book_zoho_meeting",
            description="[DEPRECATED] Use 'book_meeting' instead. This tool only works with Zoho Bookings. The new 'book_meeting' tool works with ALL integrations (Zoom, Google Calendar, Calendly, Zoho).",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Customer name"},
                    "customer_email": {"type": "string", "description": "Customer email"},
                    "customer_phone": {"type": "string", "description": "Customer phone with country code (e.g., +919876543210). Auto-filled if available."},
                    "booking_date": {"type": "string", "description": "Date in YYYY-MM-DD format (e.g., '2025-11-26'). Convert 'tomorrow' to actual date."},
                    "booking_time": {"type": "string", "description": "Time in HH:MM 24-hour format (e.g., '14:30' for 2:30 PM). Convert 12-hour to 24-hour."},
                    "duration_minutes": {"type": "integer", "description": "Duration in minutes. Default: 30"},
                    "notes": {"type": "string", "description": "Optional notes"}
                },
                "required": ["customer_name", "customer_email", "booking_date", "booking_time"]
            }
        ),
    ]


@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a tool by name"""
    if name == "list_available_integrations":
        auth_headers = get_auth_headers()
        if not auth_headers:
            return [TextContent(type="text", text="Error: Authentication not available")]

        logger.info("📋 MCP: Listing available integrations")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{settings.INTEGRATIONS_SERVICE_URL}/integrations/list",
                    headers=auth_headers
                )

                if response.status_code == 200:
                    result = response.json()
                    integrations = result.get("integrations", [])

                    # Filter only connected and active integrations
                    available = [i for i in integrations if i.get("is_connected") and i.get("is_active")]

                    if not available:
                        return [TextContent(type="text", text="No integrations are currently connected. Please ask the admin to connect integrations in the settings panel.")]

                    # Format response for AI
                    integration_list = []
                    for integration in available:
                        provider = integration.get("provider", "").upper()
                        int_type = integration.get("type", "").upper()
                        name = integration.get("name", f"{provider} {int_type}")
                        integration_list.append(f"- {name} ({provider} {int_type})")

                    response_text = f"Available integrations:\n" + "\n".join(integration_list)
                    logger.info(f"✅ Found {len(available)} connected integrations")
                    return [TextContent(type="text", text=response_text)]
                else:
                    error_msg = f"Failed to list integrations: {response.status_code}"
                    logger.error(error_msg)
                    return [TextContent(type="text", text=error_msg)]

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(error_msg)
            return [TextContent(type="text", text=error_msg)]

    elif name == "send_sms":
        phone_number = arguments.get("phone_number")
        message = arguments.get("message")

        if not phone_number or not message:
            return [TextContent(type="text", text="Error: Missing required parameters (phone_number or message)")]

        auth_headers = get_auth_headers()
        if not auth_headers:
            return [TextContent(type="text", text="Error: Authentication not available")]

        logger.info(f"📱 MCP: Sending SMS to {phone_number}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.INTEGRATIONS_SERVICE_URL}/integrations/send-sms",
                    json={"phone_number": phone_number, "message": message},
                    headers=auth_headers
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✅ SMS sent successfully: {result.get('sid')}")
                    return [TextContent(type="text", text=f"SMS sent successfully. Message ID: {result.get('sid')}")]
                else:
                    error_msg = f"Failed to send SMS: {response.status_code}"
                    logger.error(error_msg)
                    return [TextContent(type="text", text=error_msg)]

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(error_msg)
            return [TextContent(type="text", text=error_msg)]

    elif name == "send_email":
        to_email = arguments.get("to_email")
        subject = arguments.get("subject")
        body = arguments.get("body")
        html_body = arguments.get("html_body")

        if not all([to_email, subject, body]):
            return [TextContent(type="text", text="Error: Missing required parameters (to_email, subject, or body)")]

        auth_headers = get_auth_headers()
        if not auth_headers:
            return [TextContent(type="text", text="Error: Authentication not available")]

        logger.info(f"📧 MCP: Sending email to {to_email}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {"to_email": to_email, "subject": subject, "body": body}
                if html_body:
                    payload["html_body"] = html_body

                response = await client.post(
                    f"{settings.INTEGRATIONS_SERVICE_URL}/integrations/send-email",
                    json=payload,
                    headers=auth_headers
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✅ Email sent successfully to {to_email}")
                    return [TextContent(type="text", text=f"Email sent successfully to {result.get('recipient')}")]
                else:
                    error_msg = f"Failed to send email: {response.status_code}"
                    logger.error(error_msg)
                    return [TextContent(type="text", text=error_msg)]

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(error_msg)
            return [TextContent(type="text", text=error_msg)]

    elif name == "create_zoom_meeting":
        topic = arguments.get("topic")
        start_time = arguments.get("start_time")
        duration = arguments.get("duration", 60)
        timezone = arguments.get("timezone", "UTC")
        agenda = arguments.get("agenda")

        if not all([topic, start_time]):
            return [TextContent(type="text", text="Error: Missing required parameters (topic or start_time)")]

        auth_headers = get_auth_headers()
        if not auth_headers:
            return [TextContent(type="text", text="Error: Authentication not available")]

        logger.info(f"📹 MCP: Creating Zoom meeting: {topic}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "topic": topic,
                    "start_time": start_time,
                    "duration": duration,
                    "timezone": timezone
                }
                if agenda:
                    payload["agenda"] = agenda

                response = await client.post(
                    f"{settings.INTEGRATIONS_SERVICE_URL}/integrations/create-zoom-meeting",
                    json=payload,
                    headers=auth_headers
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        meeting_id = result.get("meeting_id")
                        join_url = result.get("join_url")
                        password = result.get("password")
                        logger.info(f"✅ Zoom meeting created successfully: {meeting_id}")

                        # Return conversational response that AI can use naturally
                        if password:
                            response_text = f"Meeting created successfully. The meeting ID is {meeting_id}, the join link is {join_url}, and the password is {password}."
                        else:
                            response_text = f"Meeting created successfully. The meeting ID is {meeting_id} and the join link is {join_url}."

                        return [TextContent(type="text", text=response_text)]
                    else:
                        error_msg = result.get("message", "Failed to create Zoom meeting")
                        logger.error(error_msg)
                        return [TextContent(type="text", text=error_msg)]
                else:
                    error_msg = f"Failed to create Zoom meeting: {response.status_code}"
                    logger.error(error_msg)
                    return [TextContent(type="text", text=error_msg)]

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(error_msg)
            return [TextContent(type="text", text=error_msg)]

    elif name == "book_meeting":
        customer_name = arguments.get("customer_name")
        customer_email = arguments.get("customer_email")
        customer_phone = arguments.get("customer_phone", "")
        booking_date = arguments.get("booking_date")
        booking_time = arguments.get("booking_time")
        duration_minutes = arguments.get("duration_minutes", 30)
        notes = arguments.get("notes")
        timezone = arguments.get("timezone", "Asia/Kolkata")

        if not all([customer_name, customer_email, booking_date, booking_time]):
            return [TextContent(type="text", text="Error: Missing required parameters. Need: customer_name, customer_email, booking_date, booking_time")]

        auth_headers = get_auth_headers()
        if not auth_headers:
            return [TextContent(type="text", text="Error: Authentication token not available")]

        logger.info(f"📅 MCP: Booking meeting for {customer_name} on {booking_date} at {booking_time}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "customer_phone": customer_phone,
                    "booking_date": booking_date,
                    "booking_time": booking_time,
                    "duration_minutes": duration_minutes,
                    "timezone": timezone
                }
                if notes:
                    payload["notes"] = notes

                logger.info(f"📤 Sending booking request: {json.dumps(payload, indent=2)}")
                
                response = await client.post(
                    f"{settings.INTEGRATIONS_SERVICE_URL}/integrations/book-meeting",
                    json=payload,
                    headers=auth_headers
                )

                logger.info(f"📡 Response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"📦 Response data: {json.dumps(result, indent=2)}")
                    
                    if result.get("success"):
                        integrations_used = result.get("integrations_used", [])
                        logger.info(f"✅ Meeting booked via: {', '.join(integrations_used)}")

                        # Build conversational response
                        response_text = f"Meeting booked successfully for {customer_name} on {booking_date} at {booking_time} via {', '.join(integrations_used)}!"

                        # Add Zoom details if available
                        if "zoom_meeting" in result:
                            zoom = result["zoom_meeting"]
                            response_text += f" Zoom link: {zoom.get('join_url')}"
                            if zoom.get('password'):
                                response_text += f", password: {zoom.get('password')}"

                        # Add Google Calendar/Meet details if available
                        if "google_calendar" in result:
                            gcal = result["google_calendar"]
                            if gcal.get('google_meet_link'):
                                response_text += f" Google Meet link: {gcal.get('google_meet_link')}"
                            if gcal.get('event_link'):
                                response_text += f" Calendar event: {gcal.get('event_link')}"

                        # Add Calendly details if available
                        if "calendly" in result:
                            calendly = result["calendly"]
                            if calendly.get('scheduling_link'):
                                response_text += f" Calendly link: {calendly.get('scheduling_link')}"

                        # Add Zoho Bookings details if available
                        if "zoho_bookings" in result:
                            zoho = result["zoho_bookings"]
                            if zoho.get('booking_id'):
                                response_text += f" Booking ID: {zoho.get('booking_id')}"

                        response_text += " Confirmation details have been sent to the customer."

                        return [TextContent(type="text", text=response_text)]
                    else:
                        error_msg = result.get("message", "Failed to book meeting")
                        logger.error(error_msg)
                        return [TextContent(type="text", text=error_msg)]
                else:
                    logger.error(f"❌ Booking failed with status {response.status_code}")
                    logger.error(f"📄 Response body: {response.text}")
                    
                    if response.status_code == 404:
                        error_msg = "No meeting integrations are currently connected. Please ask the admin to connect at least one integration (Zoom, Google Calendar, Calendly, or Zoho Bookings) in the settings panel."
                    elif response.status_code == 400:
                        try:
                            error_detail = response.json().get("detail", "")
                            error_msg = f"Booking validation error: {error_detail}"
                        except:
                            error_msg = "Invalid booking request. Please check the date, time, and customer details."
                    elif response.status_code == 500:
                        error_msg = "The booking system encountered an internal error. Please try again in a moment."
                    else:
                        error_msg = f"Failed to book meeting (status {response.status_code}). Please try again or contact support."
                    
                    logger.error(f"🔴 Error message to agent: {error_msg}")
                    return [TextContent(type="text", text=error_msg)]

        except httpx.TimeoutException as e:
            error_msg = "The booking system is taking too long to respond. Please try again."
            logger.error(f"⏱️ Timeout error: {str(e)}")
            return [TextContent(type="text", text=error_msg)]
        except httpx.RequestError as e:
            error_msg = "Unable to connect to the booking system. Please check if the service is running."
            logger.error(f"🔌 Connection error: {str(e)}")
            return [TextContent(type="text", text=error_msg)]
        except Exception as e:
            error_msg = f"An unexpected error occurred while booking the meeting. Please try again."
            logger.error(f"💥 Unexpected error: {str(e)}", exc_info=True)
            return [TextContent(type="text", text=error_msg)]

    elif name == "book_zoho_meeting":
        customer_name = arguments.get("customer_name")
        customer_email = arguments.get("customer_email")
        customer_phone = arguments.get("customer_phone", "")  # Optional - use if provided
        booking_date = arguments.get("booking_date")
        booking_time = arguments.get("booking_time")
        duration_minutes = arguments.get("duration_minutes", 30)
        notes = arguments.get("notes")

        if not all([customer_name, customer_email, booking_date, booking_time]):
            return [TextContent(type="text", text="Error: Missing required parameters. Need: customer_name, customer_email, booking_date, booking_time")]

        # If no phone provided, use a placeholder
        if not customer_phone:
            customer_phone = "+000000000000"  # Placeholder for when customer doesn't provide phone

        auth_headers = get_auth_headers()
        if not auth_headers:
            return [TextContent(type="text", text="Error: Authentication not available")]

        logger.info(f"📅 MCP: Booking Zoho appointment for {customer_name} on {booking_date} at {booking_time}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # First, get the Zoho Bookings integration to retrieve service_id and staff_id
                logger.info("📋 Fetching Zoho Bookings configuration...")
                integrations_response = await client.get(
                    f"{settings.INTEGRATIONS_SERVICE_URL}/integrations/list",
                    headers=auth_headers
                )

                if integrations_response.status_code != 200:
                    return [TextContent(type="text", text="Error: Failed to fetch integration settings. Please ensure Zoho Bookings is connected in admin settings.")]

                integrations = integrations_response.json().get("integrations", [])
                zoho_booking = None
                for integration in integrations:
                    if integration.get("provider") == "zoho_bookings" and integration.get("is_connected"):
                        zoho_booking = integration
                        break

                if not zoho_booking:
                    return [TextContent(type="text", text="Error: Zoho Bookings integration is not connected. Please ask the admin to connect Zoho Bookings in the settings panel.")]

                # Get the integration details to retrieve credentials with service_id and staff_id
                integration_id = zoho_booking.get("id")
                integration_detail_response = await client.get(
                    f"{settings.INTEGRATIONS_SERVICE_URL}/integrations/get/{integration_id}",
                    headers=auth_headers
                )

                if integration_detail_response.status_code != 200:
                    return [TextContent(type="text", text="Error: Failed to fetch Zoho Bookings configuration. Please ensure service and staff IDs are configured in admin settings.")]

                logger.info("✅ Zoho Bookings configuration found. Creating booking...")

                # Create the booking payload (backend will fetch service_id and staff_id from credentials)
                payload = {
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "customer_phone": customer_phone,
                    "booking_date": booking_date,
                    "booking_time": booking_time,
                    "duration_minutes": duration_minutes
                }
                if notes:
                    payload["notes"] = notes

                response = await client.post(
                    f"{settings.INTEGRATIONS_SERVICE_URL}/integrations/zoho-bookings/create-booking",
                    json=payload,
                    headers=auth_headers
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        booking_id = result.get("booking_id")
                        booking_link = result.get("booking_link")
                        logger.info(f"✅ Zoho booking created successfully: {booking_id}")

                        # Return conversational response that AI can use naturally
                        response_text = f"Appointment booked successfully for {customer_name} on {booking_date} at {booking_time}."
                        if booking_id:
                            response_text += f" Booking ID is {booking_id}."
                        if booking_link:
                            response_text += f" The booking link is {booking_link}."
                        response_text += " A confirmation with meeting link has been sent to the customer's email and phone."

                        return [TextContent(type="text", text=response_text)]
                    else:
                        error_msg = result.get("message", "Failed to create Zoho booking")
                        logger.error(error_msg)
                        return [TextContent(type="text", text=error_msg)]
                else:
                    error_msg = f"Failed to create Zoho booking: {response.status_code}"
                    if response.status_code == 404:
                        error_msg += ". Please ensure Zoho Bookings integration is connected in the admin panel."
                    elif response.status_code == 400:
                        try:
                            error_detail = response.json().get("detail", "")
                            error_msg += f". {error_detail}"
                        except:
                            pass
                    logger.error(error_msg)
                    return [TextContent(type="text", text=error_msg)]

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(error_msg)
            return [TextContent(type="text", text=error_msg)]

    raise ValueError(f"Unknown tool: {name}")
