from pydantic import BaseModel
from typing import Optional


# Zoho credentials save request (Step 1: Save client_id, client_secret)
class SaveZohoCredentialsRequest(BaseModel):
    """Request to save Zoho credentials provided by user"""
    zoho_organization_id: str  # Zoho's organization ID (e.g., "60057943135")
    client_id: str
    client_secret: str
    zoho_region: str = "in"  # Default to India, can be: com, in, eu, com.au, com.cn, jp


# Complete OAuth request (Step 3: Exchange code for tokens)
class CompleteOAuthRequest(BaseModel):
    """Request to complete OAuth flow"""
    code: str
    state: str


# Zoho CRM credentials request (Legacy)
class ZohoCRMCredentialsRequest(BaseModel):
    client_id: str
    client_secret: str
    access_token: str
    refresh_token: str
    api_domain: str


# Twilio SMS credentials request
class TwilioSMSCredentialsRequest(BaseModel):
    account_sid: str
    auth_token: str
    phone_number: str  # Twilio phone number with country code (e.g., +1234567890)


# Integration response
class IntegrationResponse(BaseModel):
    id: str
    name: str
    type: str
    provider: str
    is_active: bool
    is_connected: bool
    created_at: str
    message: Optional[str] = None

    class Config:
        from_attributes = True


# List integrations response
class IntegrationListItem(BaseModel):
    id: str
    name: str
    type: str
    provider: str
    is_active: bool
    is_connected: bool
    created_at: str

    class Config:
        from_attributes = True


class ListIntegrationsResponse(BaseModel):
    integrations: list[IntegrationListItem]


# Update integration request
class UpdateIntegrationRequest(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


# Delete response
class DeleteIntegrationResponse(BaseModel):
    message: str
    id: str


# Send SMS request
class SendSMSRequest(BaseModel):
    phone_number: str  # Recipient phone number with country code
    message: str       # SMS message content


# Send SMS response
class SendSMSResponse(BaseModel):
    success: bool
    message: str
    sid: Optional[str] = None  # Twilio message SID


# Zoom credentials request
class ZoomCredentialsRequest(BaseModel):
    account_id: str
    client_id: str
    client_secret: str


# Create Zoom meeting request
class CreateZoomMeetingRequest(BaseModel):
    topic: str
    start_time: str  # ISO format: "2024-01-15T10:00:00Z"
    duration: int = 60  # Duration in minutes
    timezone: str = "UTC"
    agenda: Optional[str] = None


# Create Zoom meeting response
class CreateZoomMeetingResponse(BaseModel):
    success: bool
    message: str
    meeting_id: Optional[str] = None
    join_url: Optional[str] = None
    password: Optional[str] = None
    start_time: Optional[str] = None


# Gmail credentials request
class GmailCredentialsRequest(BaseModel):
    email: str
    app_password: str  # Gmail App Password (16-character password)


# Send Email request
class SendEmailRequest(BaseModel):
    to_email: str
    subject: str
    body: str  # Plain text body
    html_body: Optional[str] = None  # Optional HTML body


# Send Email response
class SendEmailResponse(BaseModel):
    success: bool
    message: str
    recipient: Optional[str] = None


# Zoho Bookings credentials request (OAuth initiation)
class ZohoBookingsCredentialsRequest(BaseModel):
    client_id: str
    client_secret: str
    api_domain: str  # e.g., "bookings.zoho.in"
    workspace_id: str  # REQUIRED - Workspace ID from Zoho Bookings


# Create Booking request (called by MCP Server during call)
class CreateBookingRequest(BaseModel):
    service_id: Optional[str] = None  # Optional - Will use saved value from credentials if not provided
    staff_id: Optional[str] = None  # Optional - Will use saved value from credentials if not provided
    customer_name: str
    customer_email: str
    customer_phone: str
    booking_date: str  # Format: "YYYY-MM-DD"
    booking_time: str  # Format: "HH:MM" (24-hour format)
    duration_minutes: int = 30
    notes: Optional[str] = None


# Create Booking response
class BookingResponse(BaseModel):
    success: bool
    message: str
    booking_id: Optional[str] = None
    booking_link: Optional[str] = None
    customer_name: str
    booking_date: str
    booking_time: str
    duration_minutes: int


# Google Calendar credentials request (OAuth initiation)
class GoogleCalendarCredentialsRequest(BaseModel):
    client_id: str
    client_secret: str


# Calendly credentials request (OAuth initiation)
class CalendlyCredentialsRequest(BaseModel):
    client_id: str
    client_secret: str
    environment: str = "production"  # or "sandbox"
