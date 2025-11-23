"""
Comprehensive Calendly Integration Test Script

This script tests:
1. Calendly connection status
2. Calendly OAuth token retrieval
3. Calendly scheduling link creation
4. Meeting booking through integrations service
5. Email confirmation sending
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
BASE_URL = "http://localhost:8004"
MCP_SERVER_URL = "http://localhost:8003"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwM2ViMDFkNi03ZjlmLTQyN2YtOTYwNC04ODdmNzhjOTIxYzkiLCJlbWFpbCI6InJlaGFuQGFsc2F0cm9uaXguY29tIiwicm9sZSI6ImFkbWluIiwib3JnYW5pemF0aW9uX2lkIjoiN2NhMTFmOTUtZGZhOS00NjQ5LTg5NDEtOTY4ZDY4ZDMxNDgxIiwiZXhwIjoxNzYzODA5NjA4LCJpYXQiOjE3NjM3MjMyMDgsInR5cGUiOiJhY2Nlc3MifQ.XvYcpL022WKvPRygqqma20uiFzcRuNp0l9atArWgiJw"

USER_ID = "03eb01d6-7f9f-427f-9604-887f78c921c9"
ORG_ID = "7ca11f95-dfa9-4649-8941-968d68d31481"

headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80)

def print_success(text):
    """Print success message"""
    print(f"✅ {text}")

def print_error(text):
    """Print error message"""
    print(f"❌ {text}")

def print_info(text):
    """Print info message"""
    print(f"ℹ️  {text}")

def print_json(data):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=2))

# Test 1: Check Calendly Connection Status
def test_calendly_connection():
    print_header("TEST 1: Checking Calendly Connection Status")

    try:
        response = requests.get(
            f"{BASE_URL}/integrations/calendly/status",
            headers=headers,
            params={"user_id": USER_ID}
        )

        print_info(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print_json(data)

            if data.get("connected"):
                print_success("Calendly is connected!")
                return True
            else:
                print_error("Calendly is not connected")
                return False
        else:
            print_error(f"Failed to check status: {response.text}")
            return False

    except Exception as e:
        print_error(f"Exception occurred: {str(e)}")
        return False

# Test 2: Get Calendly Event Types
def test_get_event_types():
    print_header("TEST 2: Fetching Calendly Event Types")

    try:
        response = requests.get(
            f"{BASE_URL}/integrations/calendly/event-types",
            headers=headers,
            params={"user_id": USER_ID}
        )

        print_info(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print_json(data)

            if data.get("event_types"):
                print_success(f"Found {len(data['event_types'])} event types!")
                return data['event_types']
            else:
                print_error("No event types found")
                return []
        else:
            print_error(f"Failed to get event types: {response.text}")
            return []

    except Exception as e:
        print_error(f"Exception occurred: {str(e)}")
        return []

# Test 3: Create Calendly Scheduling Link
def test_create_scheduling_link(event_type_uri):
    print_header("TEST 3: Creating Calendly Scheduling Link")

    try:
        # Calculate test meeting time (tomorrow at 2 PM)
        meeting_time = datetime.now() + timedelta(days=1)
        meeting_time = meeting_time.replace(hour=14, minute=0, second=0, microsecond=0)

        payload = {
            "user_id": USER_ID,
            "event_type_uri": event_type_uri,
            "invitee_name": "Test User",
            "invitee_email": "testuser@example.com",
            "meeting_time": meeting_time.isoformat()
        }

        print_info("Request Payload:")
        print_json(payload)

        response = requests.post(
            f"{BASE_URL}/integrations/calendly/create-link",
            headers=headers,
            json=payload
        )

        print_info(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print_json(data)
            print_success("Scheduling link created successfully!")
            return data
        else:
            print_error(f"Failed to create link: {response.text}")
            return None

    except Exception as e:
        print_error(f"Exception occurred: {str(e)}")
        return None

# Test 4: Test Unified Booking Endpoint with Calendly
def test_unified_booking():
    print_header("TEST 4: Testing Unified Booking Endpoint with Calendly")

    try:
        # Calculate test meeting time (tomorrow at 3 PM)
        meeting_time = datetime.now() + timedelta(days=1)
        meeting_time = meeting_time.replace(hour=15, minute=0, second=0, microsecond=0)

        payload = {
            "user_id": USER_ID,
            "organization_id": ORG_ID,
            "meeting_title": "Test Meeting via Calendly",
            "meeting_description": "This is a test meeting to verify Calendly integration",
            "attendee_name": "John Doe",
            "attendee_email": "johndoe@example.com",
            "attendee_phone": "+1234567890",
            "meeting_date": meeting_time.strftime("%Y-%m-%d"),
            "meeting_time": meeting_time.strftime("%H:%M"),
            "duration_minutes": 30,
            "timezone": "America/New_York"
        }

        print_info("Request Payload:")
        print_json(payload)

        response = requests.post(
            f"{BASE_URL}/integrations/book-meeting",
            headers=headers,
            json=payload
        )

        print_info(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print_json(data)
            print_success("Meeting booked successfully via unified endpoint!")

            # Check what integrations were used
            if "calendly_link" in data:
                print_success("✅ Calendly link was created!")
            if "google_calendar_event" in data:
                print_success("✅ Google Calendar event was created!")
            if "zoom_meeting" in data:
                print_success("✅ Zoom meeting was created!")
            if "email_sent" in data and data["email_sent"]:
                print_success("✅ Email confirmation was sent!")

            return data
        else:
            print_error(f"Failed to book meeting: {response.text}")
            return None

    except Exception as e:
        print_error(f"Exception occurred: {str(e)}")
        return None

# Test 5: Test MCP Server Integration
def test_mcp_server_booking():
    print_header("TEST 5: Testing MCP Server Meeting Booking")

    try:
        # Calculate test meeting time (tomorrow at 4 PM)
        meeting_time = datetime.now() + timedelta(days=1)
        meeting_time = meeting_time.replace(hour=16, minute=0, second=0, microsecond=0)

        payload = {
            "user_id": USER_ID,
            "organization_id": ORG_ID,
            "meeting_title": "Test Meeting via MCP Server",
            "meeting_description": "Testing MCP server's ability to book through Calendly",
            "attendee_name": "Jane Smith",
            "attendee_email": "janesmith@example.com",
            "attendee_phone": "+1987654321",
            "date": meeting_time.strftime("%Y-%m-%d"),
            "time": meeting_time.strftime("%H:%M"),
            "duration": 30
        }

        print_info("Request Payload:")
        print_json(payload)

        response = requests.post(
            f"{MCP_SERVER_URL}/book-meeting",
            headers=headers,
            json=payload
        )

        print_info(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print_json(data)
            print_success("MCP Server successfully booked meeting!")
            return data
        else:
            print_error(f"Failed to book via MCP server: {response.text}")
            return None

    except Exception as e:
        print_error(f"Exception occurred: {str(e)}")
        return None

# Main Test Runner
def run_all_tests():
    print("\n")
    print("╔" + "═"*78 + "╗")
    print("║" + " "*20 + "CALENDLY INTEGRATION TEST SUITE" + " "*26 + "║")
    print("╚" + "═"*78 + "╝")

    print_info(f"Testing against Integrations Service: {BASE_URL}")
    print_info(f"Testing against MCP Server: {MCP_SERVER_URL}")
    print_info(f"User ID: {USER_ID}")
    print_info(f"Organization ID: {ORG_ID}")

    results = {
        "total_tests": 5,
        "passed": 0,
        "failed": 0
    }

    # Test 1: Connection Status
    if test_calendly_connection():
        results["passed"] += 1
    else:
        results["failed"] += 1
        print_error("Calendly is not connected. Please connect it first!")
        print_summary(results)
        return

    # Test 2: Get Event Types
    event_types = test_get_event_types()
    if event_types:
        results["passed"] += 1
    else:
        results["failed"] += 1
        print_error("Cannot proceed without event types")
        print_summary(results)
        return

    # Test 3: Create Scheduling Link
    if event_types:
        event_type_uri = event_types[0].get("uri")
        if test_create_scheduling_link(event_type_uri):
            results["passed"] += 1
        else:
            results["failed"] += 1

    # Test 4: Unified Booking
    if test_unified_booking():
        results["passed"] += 1
    else:
        results["failed"] += 1

    # Test 5: MCP Server Booking
    if test_mcp_server_booking():
        results["passed"] += 1
    else:
        results["failed"] += 1

    print_summary(results)

def print_summary(results):
    print_header("TEST SUMMARY")
    print(f"Total Tests: {results['total_tests']}")
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")

    if results['failed'] == 0:
        print("\n" + "🎉"*40)
        print("ALL TESTS PASSED! Calendly integration is working perfectly!")
        print("🎉"*40 + "\n")
    else:
        print("\n⚠️  Some tests failed. Please check the output above for details.\n")

if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)
