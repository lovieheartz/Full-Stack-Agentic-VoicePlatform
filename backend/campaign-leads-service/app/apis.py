from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Campaign, CampaignStatus
from app.schemas import CreateCampaignRequest, CampaignResponse, ListCampaignsResponse, CampaignListItem
from app.security import get_current_user
from datetime import datetime
import uuid
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/campaigns/create-campaign", response_model=CampaignResponse)
async def create_campaign(
    request: CreateCampaignRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new campaign

    **Request body:**
    - name: Campaign name
    - description: Campaign description (optional)
    - agent_id: UUID of the agent to use
    - start_date: Campaign start date (YYYY-MM-DD)
    - end_date: Campaign end date (YYYY-MM-DD, optional)
    - max_call_attempts: Maximum call attempts per lead (default: 3)
    """
    try:
        organization_id = current_user["organization_id"]
        user_id = current_user["sub"]  # JWT uses 'sub' for user ID

        logger.info(f"Creating campaign: {request.name} for organization: {organization_id}")

        # Parse dates
        try:
            start_date_obj = datetime.strptime(request.start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.strptime(request.end_date, "%Y-%m-%d").date() if request.end_date else None
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format. Use YYYY-MM-DD: {str(e)}")

        # Validate end_date is after start_date
        if end_date_obj and end_date_obj < start_date_obj:
            raise HTTPException(status_code=400, detail="End date must be after start date")

        # Create campaign
        new_campaign = Campaign(
            organization_id=uuid.UUID(organization_id),
            user_id=uuid.UUID(user_id),
            agent_id=uuid.UUID(request.agent_id),
            name=request.name,
            description=request.description,
            status=CampaignStatus.DRAFT,
            start_date=start_date_obj,
            end_date=end_date_obj,
            max_call_attempts=request.max_call_attempts
        )

        db.add(new_campaign)
        db.commit()
        db.refresh(new_campaign)

        logger.info(f"Campaign created successfully - ID: {new_campaign.id}")

        return CampaignResponse(
            id=str(new_campaign.id),
            name=new_campaign.name,
            description=new_campaign.description,
            agent_id=str(new_campaign.agent_id),
            status=new_campaign.status.value,
            start_date=new_campaign.start_date.isoformat(),
            end_date=new_campaign.end_date.isoformat() if new_campaign.end_date else None,
            max_call_attempts=new_campaign.max_call_attempts,
            created_at=new_campaign.created_at.isoformat(),
            message=f"Campaign '{request.name}' created successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create campaign: {str(e)}")


@router.get("/campaigns/list-campaign", response_model=ListCampaignsResponse)
async def list_campaigns(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of campaigns for the organization

    Returns all campaigns belonging to the user's organization,
    ordered by creation date (newest first).
    """
    try:
        organization_id = current_user["organization_id"]
        logger.info(f"Fetching campaigns for organization: {organization_id}")

        # Get all campaigns for this organization
        campaigns = db.query(Campaign).filter(
            Campaign.organization_id == uuid.UUID(organization_id)
        ).order_by(Campaign.created_at.desc()).all()

        logger.info(f"Found {len(campaigns)} campaigns")

        # Convert to response format
        campaign_list = [
            CampaignListItem(
                id=str(campaign.id),
                name=campaign.name,
                description=campaign.description,
                agent_id=str(campaign.agent_id),
                status=campaign.status.value,
                start_date=campaign.start_date.isoformat(),
                end_date=campaign.end_date.isoformat() if campaign.end_date else None,
                max_call_attempts=campaign.max_call_attempts,
                created_at=campaign.created_at.isoformat(),
                updated_at=campaign.updated_at.isoformat()
            )
            for campaign in campaigns
        ]

        return ListCampaignsResponse(
            campaigns=campaign_list
        )

    except Exception as e:
        logger.error(f"Error fetching campaigns: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch campaigns: {str(e)}")


@router.get("/campaigns/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "campaign-leads-service"}
