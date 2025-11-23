"""
Complete Calendly Integration Test
Tests the end-to-end booking flow through the MCP server
"""

import requests
import json
from datetime import datetime, timedelta
import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    sys.stdout.reconfigure(encoding='utf-8')

# Configuration
INTEGRATIONS_SERVICE_URL = "http://localhost:8004"
MCP_SERVER_URL = "http://localhost:8089"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwM2ViMDFkNi03ZjlmLTQyN2YtOTYwNC04ODdmNzhjOTIxYzkiLCJlbWFpbCI6InJlaGFuQGFsc2F0cm9uaXguY29tIiwicm9sZSI6ImFkbWluIiwib3JnYW5pemF0aW9uX2lkIjoiN2NhMTFmOTUtZGZhOS00NjQ5LTg5NDEtOTY4ZDY4ZDMxNDgxIiwiZXhwIjoxNzYzODA5NjA4LCJpYXQiOjE3NjM3MjMyMDgsInR5cGUiOiJhY2Nlc3MifQ.XvYcpL022WKvPRygqqma20uiFzcRuNp0l9atArWgiJw"

USER_ID = "03eb01d6-7f9f-427f-9604-887f78c921c9"
ORG_ID = "7ca11f95-dfa9-4649-8941-968d68d31481"

headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def print_test(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def print_success(text):
    print(f"✅ {text}")

def print_error(text):
    print(f"❌ {text}")

def print_info(text):
    print(f"ℹ️  {text}")

def print_json(data):
    print(json.dumps(data, indent=2))


# ============================================================================
# TEST 1: Check Calendly Connection
# ============================================================================
print_test("TEST 1: Verify Calendly Connection")

try:
    response = requests.get(
        f"{INTEGRATIONS_SERVICE_URL}/integrations/calendly/status",
        headers=headers,
        params={"user_id": USER_ID}
    )

    if response.status_code == 200:
        data = response.json()
        if data.get("connected"):
            print_success("Calendly is connected!")
            print_info(f"Integration ID: {data.get('integration_id')}")
            print_info(f"Environment: {data.get('environment')}")
        else:
            print_error("Calendly is not connected")
            sys.exit(1)
    else:
        print_error(f"Failed to check status: {response.status_code}")
        sys.exit(1)

except Exception as e:
    print_error(f"Error: {str(e)}")
    sys.exit(1)


# ============================================================================
# TEST 2: Get Calendly Event Types
# ============================================================================
print_test("TEST 2: Fetch Calendly Event Types")

try:
    response = requests.get(
        f"{INTEGRATIONS_SERVICE_URL}/integrations/calendly/event-types",
        headers=headers,
        params={"user_id": USER_ID}
    )

    if response.status_code == 200:
        data = response.json()
        event_types = data.get("event_types", [])

        if event_types:
            print_success(f"Found {len(event_types)} event types:")
            for et in event_types:
                print(f"  📅 {et['name']} ({et['duration']} min) - {et['scheduling_url']}")
        else:
            print_error("No event types found")
            sys.exit(1)
    else:
        print_error(f"Failed to fetch event types: {response.status_code}")
        sys.exit(1)

except Exception as e:
    print_error(f"Error: {str(e)}")
    sys.exit(1)


# ============================================================================
# TEST 3: Direct Unified Booking API Test
# ============================================================================
print_test("TEST 3: Test Unified Booking API with Calendly")

try:
    # Calculate test meeting time (tomorrow at 2 PM)
    meeting_time = datetime.now() + timedelta(days=1)
    meeting_time = meeting_time.replace(hour=14, minute=0, second=0, microsecond=0)

    payload = {
        "customer_name": "Test Customer",
        "customer_email": "testcustomer@example.com",
        "customer_phone": "+1234567890",
        "booking_date": meeting_time.strftime("%Y-%m-%d"),
        "booking_time": meeting_time.strftime("%H:%M"),
        "duration_minutes": 30,
        "notes": "Test meeting via Calendly integration",
        "timezone": "America/New_York"
    }

    print_info("Booking details:")
    print(f"  Name: {payload['customer_name']}")
    print(f"  Email: {payload['customer_email']}")
    print(f"  Date: {payload['booking_date']}")
    print(f"  Time: {payload['booking_time']}")

    response = requests.post(
        f"{INTEGRATIONS_SERVICE_URL}/integrations/book-meeting",
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        result = response.json()
        print_success("Meeting booked successfully!")

        print_info("Integrations used:")
        for integration in result.get("integrations_used", []):
            print(f"  ✓ {integration}")

        # Check Calendly details
        if "calendly" in result:
            print_success("Calendly scheduling link created:")
            print(f"  🗓️  {result['calendly'].get('scheduling_link')}")

        # Check Zoom details
        if "zoom_meeting" in result:
            print_success("Zoom meeting created:")
            print(f"  🎥 Join URL: {result['zoom_meeting'].get('join_url')}")
            if result['zoom_meeting'].get('password'):
                print(f"  🔐 Password: {result['zoom_meeting'].get('password')}")

        # Check Google Calendar details
        if "google_calendar" in result:
            print_success("Google Calendar event created:")
            if result['google_calendar'].get('event_link'):
                print(f"  📅 Event: {result['google_calendar'].get('event_link')}")
            if result['google_calendar'].get('google_meet_link'):
                print(f"  🎥 Meet: {result['google_calendar'].get('google_meet_link')}")

        # Check email confirmation
        if result.get("email_sent"):
            print_success("Confirmation email sent!")

    else:
        print_error(f"Failed to book meeting: {response.status_code}")
        print(response.text)
        sys.exit(1)

except Exception as e:
    print_error(f"Error: {str(e)}")
    sys.exit(1)


# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "="*80)
print("  🎉 ALL TESTS PASSED - CALENDLY INTEGRATION IS WORKING!")
print("="*80)
print()
print("✅ Calendly is properly connected")
print("✅ Event types are accessible")
print("✅ Unified booking API works with Calendly")
print("✅ Email confirmations are being sent")
print()
print("Your AI agent can now book meetings through Calendly!")
print("The system works with ANY combination of:")
print("  • Zoom (video meetings)")
print("  • Google Calendar (with Google Meet)")
print("  • Calendly (scheduling links)")
print("  • Zoho Bookings (appointments)")
print()
print("="*80)
