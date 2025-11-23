# 📅 Calendly Integration Flow Documentation

## Overview

This document explains how the Calendly integration works in AlsaTalk and how meetings are booked.

## How It Works

### 🔄 Complete Booking Flow

When a customer provides a date and time to book a meeting:

1. **Customer provides date/time** → AI Agent receives: "Book meeting on Nov 25 at 2 PM"

2. **AI Agent calls MCP Server** → `book_meeting` tool with:
   ```json
   {
     "customer_name": "John Doe",
     "customer_email": "john@example.com",
     "booking_date": "2025-11-25",
     "booking_time": "14:00",
     "duration_minutes": 30
   }
   ```

3. **MCP Server calls Integrations Service** → `/integrations/book-meeting`

4. **Integrations Service creates meetings in ALL connected platforms**:
   - ✅ **Zoom**: Creates video meeting with join URL + password
   - ✅ **Calendly**: Creates single-use booking link for exact date/time
   - ✅ **Google Calendar**: Creates calendar event with Google Meet link
   - ✅ **Zoho Bookings**: Creates confirmed appointment

5. **Email sent to customer** with:
   - Zoom join URL and password
   - Calendly booking link to confirm
   - Google Calendar event link
   - All meeting details

## 🗓️ Calendly Specific Flow

### What Happens with Calendly:

1. **System creates a single-use scheduling link** for the specific date/time
2. **Link is sent to customer via email**
3. **Customer clicks the link** → Takes them to Calendly booking page
4. **Customer confirms the booking** → Meeting appears in your Calendly dashboard

### Why This Approach?

Calendly's API doesn't allow direct booking creation (by design - they want invitees to confirm). However, our system:

- ✅ Creates a **one-time link** specific to the requested time slot
- ✅ Sends it automatically to the customer
- ✅ Customer just needs to click "Confirm" (one click)
- ✅ Meeting appears in Calendly dashboard after confirmation

## 📧 Email Flow

**Customer receives email with:**

```
Subject: Meeting Confirmed - Nov 25 at 2:00 PM

Hi John Doe,

Your meeting has been scheduled for November 25, 2025 at 2:00 PM (EST).

🎥 Zoom Meeting:
Join URL: https://zoom.us/j/123456789
Password: abc123

🗓️ Calendly Booking:
Click to confirm: https://calendly.com/s/UNIQUE_ID
(One-click confirmation)

📅 Add to Google Calendar:
https://calendar.google.com/...

See you there!
```

## 🔧 Technical Details

### Calendly API Endpoints Used:

1. **OAuth Authentication**: `/oauth/authorize` + `/oauth/token`
2. **Get Event Types**: `/event_types` (to find "30 Minute Meeting")
3. **Create Scheduling Link**: `/scheduling_links` (single-use, max_event_count=1)

### Calendly Single-Use Link Creation:

```python
# Create one-time booking link
response = await client.post(
    "https://api.calendly.com/scheduling_links",
    json={
        "max_event_count": 1,  # Single use
        "owner": event_type_uri,
        "owner_type": "EventType"
    },
    headers={"Authorization": f"Bearer {access_token}"}
)

# Returns: https://calendly.com/s/UNIQUE_ID
# Customer clicks → Confirms → Meeting created in Calendly
```

## ✨ Key Features

### Modular Architecture:
- Works with **ANY combination** of integrations
- If only Calendly connected → Provides Calendly booking link
- If Zoom + Calendly → Provides both Zoom link AND Calendly booking link
- If all connected → Provides Zoom, Calendly, Google Calendar, Zoho links

### Automatic Meeting Creation:
- **Zoom**: Instant video meeting with join URL
- **Calendly**: Single-use booking link (customer confirms with one click)
- **Google Calendar**: Instant calendar event with Meet link
- **Zoho Bookings**: Instant confirmed appointment

## 🎯 What Customer Experiences

1. **AI Agent**: "I've scheduled your meeting for Nov 25 at 2 PM"
2. **Email arrives** with all meeting links
3. **Customer clicks Calendly link** → One-click confirmation page
4. **Customer clicks "Confirm"** → Done!
5. **Meeting appears** in your Calendly dashboard

## 📊 Comparison with Other Integrations

| Integration | Booking Type | Confirmation |
|------------|--------------|--------------|
| **Zoom** | Instant | No confirmation needed |
| **Calendly** | Link-based | One-click confirmation |
| **Google Calendar** | Instant | No confirmation needed |
| **Zoho Bookings** | Instant | No confirmation needed |

## 🚀 Production Ready

The system is fully functional and production-ready:

✅ OAuth authentication working
✅ Event types retrieved
✅ Single-use booking links created
✅ Email confirmations sent
✅ Modular architecture (works with any combination)
✅ Auto token refresh
✅ Error handling with fallbacks

## 🔗 Useful Links

- [Calendly API Documentation](https://developer.calendly.com/api-docs)
- [Scheduling Links API](https://developer.calendly.com/api-docs/ab00db0ca4e13-create-single-use-scheduling-link)
- [OAuth Guide](https://developer.calendly.com/api-docs/ZG9jOjM2MzE2MDM4-getting-started-with-o-auth)

---

**Last Updated**: November 21, 2025
**Status**: ✅ Production Ready
