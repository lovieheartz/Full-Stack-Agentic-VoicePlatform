from pydantic import BaseModel
from typing import Optional
from datetime import date


# Create Campaign Request
class CreateCampaignRequest(BaseModel):
    name: str
    description: Optional[str] = None
    agent_id: str  # UUID string
    start_date: str  # ISO date string (YYYY-MM-DD)
    end_date: Optional[str] = None  # Optional ISO date string
    max_call_attempts: int = 3


# Campaign Response
class CampaignResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    agent_id: str
    status: str
    start_date: str
    end_date: Optional[str]
    max_call_attempts: int
    created_at: str
    message: Optional[str] = None

    class Config:
        from_attributes = True


# List Campaigns Response
class CampaignListItem(BaseModel):
    id: str
    name: str
    description: Optional[str]
    agent_id: str
    status: str
    start_date: str
    end_date: Optional[str]
    max_call_attempts: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ListCampaignsResponse(BaseModel):
    campaigns: list[CampaignListItem]
