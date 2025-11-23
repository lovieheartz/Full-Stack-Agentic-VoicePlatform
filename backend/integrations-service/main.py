from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.apis import router
from app.integrations.zoom import router as zoom_router
from app.integrations.twilio import router as twilio_router
from app.integrations.gmail import router as gmail_router
from app.integrations.zoho import router as zoho_router
from app.integrations.zoho_bookings import router as zoho_bookings_router
from app.integrations.google_calendar import router as google_calendar_router
from app.integrations.calendly import router as calendly_router
from app.integrations.unified_booking import router as unified_booking_router
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)
app.include_router(zoom_router)
app.include_router(twilio_router)
app.include_router(gmail_router)
app.include_router(zoho_router)
app.include_router(zoho_bookings_router)
app.include_router(google_calendar_router)
app.include_router(calendly_router)
app.include_router(unified_booking_router)


@app.get("/")
async def root():
    return {"message": "AlsaTalk Integrations Service", "status": "active"}
