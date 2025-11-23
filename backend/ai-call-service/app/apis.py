from fastapi import APIRouter, HTTPException, Depends, Security
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.schemas import (
    TriggerCallRequest, TriggerCallResponse, TriggerDirectCallRequest,
    CreateAgentRequest, CreateAgentResponse, UpdateAgentRequest, UpdateAgentResponse,
    ListAgentsResponse, AgentDetails, RoomTokenResponse,
    ListCallHistoryResponse, CallHistoryItem,
    AssignAgentRequest, UnassignAgentRequest, AssignmentResponse, ListAssignedUsersResponse, AssignedUserDetails,
    CreateInboundAgentRequest, CreateInboundAgentResponse, ListInboundAgentsResponse, InboundAgentDetails,
    UpdateInboundAgentRequest, UpdateInboundAgentResponse
)
from app.database import get_db
from app.models import Agent, AgentType, Lead, Call, CallDirection, User, UserAgent, UserRole
from app.security import get_current_user, security_scheme
from app.config import settings
from app.instructions.outbound_instructions import build_instructions_outbound
from livekit import api
import json
import random
import logging
import os
import uuid
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/ai-call/calls/trigger", response_model=TriggerCallResponse)
async def trigger_outbound_call(
    request: TriggerCallRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Security(security_scheme)
):
    """
    Trigger an outbound call to a phone number

    - **lead_id**: UUID of the lead from database
    - **agent_id**: UUID of the agent from database
    - **phone_number**: Phone number to call (with country code)
    - **sip_trunk_id**: SIP trunk ID for the call
    """
    try:
        organization_id = current_user["organization_id"]
        logger.info(f"Triggering call for lead: {request.lead_id}, agent: {request.agent_id}, org: {organization_id}")

        # Fetch agent from database
        agent = db.query(Agent).filter(
            Agent.id == uuid.UUID(request.agent_id),
            Agent.organization_id == uuid.UUID(organization_id)
        ).first()

        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        if not agent.is_active:
            raise HTTPException(status_code=400, detail="Agent is not active")

        # Fetch lead from database
        lead = db.query(Lead).filter(
            Lead.id == uuid.UUID(request.lead_id),
            Lead.organization_id == uuid.UUID(organization_id)
        ).first()

        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        # Build lead data dict
        lead_data = {
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "email": lead.email,
            "phone_number": request.phone_number,
            "company": lead.company,
            "extra_data": lead.extra_data
        }

        # Combine tone + agent prompt + lead data + opening message + capabilities into final instructions
        final_instructions = build_instructions_outbound(
            agent_prompt=agent.system_prompt,
            lead_data=lead_data,
            opening_message=agent.opening_message,
            capabilities=agent.capabilities
        )

        # Initialize LiveKit API
        lkapi = api.LiveKitAPI(
            url=settings.LIVEKIT_URL,
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET
        )

        # Generate unique room name
        room_name = f"call-{request.lead_id}-{''.join(str(random.randint(0, 9)) for _ in range(6))}"

        # Prepare call metadata with agent and lead data
        call_metadata = {
            "lead_id": request.lead_id,
            "agent_id": request.agent_id,
            "phone_number": request.phone_number,
            "sip_trunk_id": request.sip_trunk_id,
            "instructions": final_instructions,
            "opening_message": agent.opening_message,
            "voice_id": agent.voice_id,
            "organization_id": organization_id,
            "jwt_token": credentials.credentials  # Pass JWT token for function calling
        }

        # Dispatch agent (agent UUID as worker name)
        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name="AlsaTalkOutboundAgent",
                room=room_name,
                metadata=json.dumps(call_metadata)
            )
        )

        await lkapi.aclose()

        logger.info(f"Call dispatched successfully - Room: {room_name}")

        return TriggerCallResponse(
            status="success",
            room_name=room_name,
            # message=f"Call initiated for lead {lead.first_name} {lead.last_name}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering call: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger call: {str(e)}")


@router.post("/ai-call/calls/trigger-direct", response_model=TriggerCallResponse)
async def trigger_direct_call(
    request: TriggerDirectCallRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Security(security_scheme)
):
    """
    Trigger a direct outbound call without requiring a lead

    - **agent_id**: UUID of the agent from database
    - **phone_number**: Phone number to call (with country code)
    - **sip_trunk_id**: SIP trunk ID for the call

    Use this endpoint for ad-hoc calls, testing, or when calling numbers not in your leads database.
    """
    try:
        organization_id = current_user["organization_id"]
        logger.info(f"Triggering direct call - agent: {request.agent_id}, phone: {request.phone_number}, org: {organization_id}")

        # Fetch agent from database
        agent = db.query(Agent).filter(
            Agent.id == uuid.UUID(request.agent_id),
            Agent.organization_id == uuid.UUID(organization_id)
        ).first()

        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        if not agent.is_active:
            raise HTTPException(status_code=400, detail="Agent is not active")

        # Use empty lead data for direct calls (only phone number is known)
        lead_data = {
            "first_name": None,
            "last_name": None,
            "email": None,
            "phone_number": request.phone_number,
            "company": None,
            "extra_data": {}
        }

        # Build instructions with lead data + opening message + capabilities
        final_instructions = build_instructions_outbound(
            agent_prompt=agent.system_prompt,
            lead_data=lead_data,
            opening_message=agent.opening_message,
            capabilities=agent.capabilities
        )

        # Initialize LiveKit API
        lkapi = api.LiveKitAPI(
            url=settings.LIVEKIT_URL,
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET
        )

        # Generate unique room name with random ID
        random_id = str(uuid.uuid4())
        room_name = f"call-direct-{random_id[:8]}-{''.join(str(random.randint(0, 9)) for _ in range(6))}"

        # Prepare call metadata
        call_metadata = {
            "lead_id": None,
            "agent_id": request.agent_id,
            "phone_number": request.phone_number,
            "sip_trunk_id": request.sip_trunk_id,
            "instructions": final_instructions,
            "opening_message": agent.opening_message,
            "voice_id": agent.voice_id,
            "organization_id": organization_id,
            "jwt_token": credentials.credentials  # Pass JWT token for function calling
        }

        # Create Call record in database
        new_call = Call(
            organization_id=uuid.UUID(organization_id),
            user_id=uuid.UUID(current_user["sub"]),  # "sub" contains user_id from JWT token
            agent_id=agent.id,
            direction=CallDirection.OUTBOUND,
            from_number=None,  # Will be set by SIP provider
            to_number=request.phone_number,
            room_name=room_name,
            status="initiated",
            started_at=datetime.utcnow()
        )
        db.add(new_call)
        db.commit()
        db.refresh(new_call)

        logger.info(f"Call record created - ID: {new_call.id}, Room: {room_name}")

        # Dispatch agent
        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name="AlsaTalkOutboundAgent",
                room=room_name,
                metadata=json.dumps(call_metadata)
            )
        )

        await lkapi.aclose()

        logger.info(f"Direct call dispatched successfully - Room: {room_name}")

        return TriggerCallResponse(
            status="success",
            room_name=room_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering direct call: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger direct call: {str(e)}")


@router.get("/ai-call/agents", response_model=ListAgentsResponse)
async def list_agents(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of outbound agents

    - **Admin**: Returns ALL agents in the organization
    - **Regular User**: Returns ONLY agents assigned to them

    Returns a list of agents with their details including name, language, voice, status, etc.
    """
    try:
        organization_id = current_user["organization_id"]
        user_id = current_user["sub"]  # JWT uses 'sub' for user ID
        user_role = current_user["role"]

        logger.info(f"Fetching agents for organization: {organization_id}, user: {user_id}, role: {user_role}")

        if user_role == "admin":
            # Admin sees ALL agents in the organization
            agents = db.query(Agent).filter(
                Agent.organization_id == uuid.UUID(organization_id),
                Agent.type == AgentType.OUTBOUND
            ).order_by(Agent.created_at.desc()).all()

            logger.info(f"Admin access: returning all {len(agents)} agents")
        else:
            # Regular user sees ONLY assigned agents
            agents = db.query(Agent).join(
                UserAgent, Agent.id == UserAgent.agent_id
            ).filter(
                Agent.organization_id == uuid.UUID(organization_id),
                Agent.type == AgentType.OUTBOUND,
                UserAgent.user_id == uuid.UUID(user_id),
                UserAgent.is_active == True
            ).order_by(Agent.created_at.desc()).all()

            logger.info(f"User access: returning {len(agents)} assigned agents")

        # Convert to response format
        agent_list = [
            AgentDetails(
                id=str(agent.id),
                name=agent.name,
                language=agent.language,
                opening_message=agent.opening_message,
                system_prompt=agent.system_prompt,
                voice_id=agent.voice_id,
                status="active" if agent.is_active else "inactive",
                created_at=agent.created_at.isoformat(),
                capabilities=agent.capabilities
            )
            for agent in agents
        ]

        return ListAgentsResponse(
            agents=agent_list,
            total=len(agent_list)
        )

    except Exception as e:
        logger.error(f"Error fetching agents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch agents: {str(e)}")


@router.post("/ai-call/agents", response_model=CreateAgentResponse)
async def create_agent(
    request: CreateAgentRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new outbound agent

    - **agent_name**: Name of the agent
    - **language**: Language for the agent (e.g., "English", "Hindi", "Spanish")
    - **opening_message**: Initial greeting message
    - **ai_instructions**: System prompt for AI behavior
    - **status**: Active status (true/false)
    """
    try:
        organization_id = current_user["organization_id"]
        logger.info(f"Creating agent: {request.agent_name} for organization: {organization_id}")

        # Create agent record
        new_agent = Agent(
            organization_id=uuid.UUID(organization_id),
            name=request.agent_name,
            type=AgentType.OUTBOUND,
            language=request.language,
            opening_message=request.opening_message,
            system_prompt=request.ai_instructions,
            is_active=request.status,
            capabilities=request.capabilities if request.capabilities else {}
        )

        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)

        logger.info(f"Agent created successfully - ID: {new_agent.id}")

        return CreateAgentResponse(
            id=str(new_agent.id),
            agent_name=new_agent.name,
            status="active" if new_agent.is_active else "inactive",
            message=f"Agent '{request.agent_name}' created successfully"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")


@router.put("/ai-call/agents/{agent_id}", response_model=UpdateAgentResponse)
async def update_agent(
    agent_id: str,
    request: UpdateAgentRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing outbound agent

    - **agent_name**: Name of the agent (optional)
    - **language**: Language for the agent (optional)
    - **opening_message**: Initial greeting message (optional)
    - **ai_instructions**: System prompt for AI behavior (optional)
    - **status**: Active status (optional)
    """
    try:
        organization_id = current_user["organization_id"]
        logger.info(f"Updating agent: {agent_id} for organization: {organization_id}")

        # Fetch agent from database
        agent = db.query(Agent).filter(
            Agent.id == uuid.UUID(agent_id),
            Agent.organization_id == uuid.UUID(organization_id)
        ).first()

        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Update fields if provided
        if request.agent_name is not None:
            agent.name = request.agent_name
        if request.language is not None:
            agent.language = request.language
        if request.opening_message is not None:
            agent.opening_message = request.opening_message
        if request.ai_instructions is not None:
            agent.system_prompt = request.ai_instructions
        if request.status is not None:
            agent.is_active = request.status
        if request.capabilities is not None:
            agent.capabilities = request.capabilities

        db.commit()
        db.refresh(agent)

        logger.info(f"Agent updated successfully - ID: {agent.id}")

        return UpdateAgentResponse(
            id=str(agent.id),
            agent_name=agent.name,
            status="active" if agent.is_active else "inactive",
            message=f"Agent '{agent.name}' updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update agent: {str(e)}")


@router.post("/ai-call/agents/inbound", response_model=CreateInboundAgentResponse)
async def create_inbound_agent(
    request: CreateInboundAgentRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new inbound agent

    - **agent_name**: Name of the agent
    - **language**: Language for the agent (e.g., "English", "Hindi", "Spanish")
    - **greeting**: Greeting message when answering calls
    - **ai_instructions**: System prompt for AI behavior
    - **voice_id**: Voice ID (e.g., "shimmer", "alloy", "echo")
    - **inbound_phone_number**: Phone number for receiving calls
    - **status**: Active status (true/false)
    - **capabilities**: Agent capabilities (SMS, WhatsApp, Email, Booking)
    """
    try:
        organization_id = current_user["organization_id"]
        logger.info(f"Creating inbound agent: {request.agent_name} for organization: {organization_id}")

        # Create inbound agent record
        new_agent = Agent(
            organization_id=uuid.UUID(organization_id),
            name=request.agent_name,
            type=AgentType.INBOUND,
            language=request.language,
            opening_message=request.greeting,
            system_prompt=request.ai_instructions,
            voice_id=request.voice_id,
            inbound_phone_number=request.inbound_phone_number,
            is_active=request.status,
            capabilities=request.capabilities if request.capabilities else {}
        )

        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)

        logger.info(f"Inbound agent created successfully - ID: {new_agent.id}, Phone: {request.inbound_phone_number}")

        return CreateInboundAgentResponse(
            id=str(new_agent.id),
            agent_name=new_agent.name,
            inbound_phone_number=new_agent.inbound_phone_number,
            status="active" if new_agent.is_active else "inactive",
            message=f"Inbound agent '{request.agent_name}' created successfully"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating inbound agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create inbound agent: {str(e)}")


@router.get("/ai-call/agents/inbound", response_model=ListInboundAgentsResponse)
async def list_inbound_agents(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of inbound agents

    - **Admin**: Returns ALL inbound agents in the organization
    - **Regular User**: Returns ONLY inbound agents assigned to them

    Returns a list of inbound agents with their details including name, language, greeting, phone number, etc.
    """
    try:
        organization_id = current_user["organization_id"]
        user_id = current_user["sub"]  # JWT uses 'sub' for user ID
        user_role = current_user["role"]

        logger.info(f"Fetching inbound agents for organization: {organization_id}, user: {user_id}, role: {user_role}")

        if user_role == "admin":
            # Admin sees ALL inbound agents in the organization
            agents = db.query(Agent).filter(
                Agent.organization_id == uuid.UUID(organization_id),
                Agent.type == AgentType.INBOUND
            ).order_by(Agent.created_at.desc()).all()

            logger.info(f"Admin access: returning all {len(agents)} inbound agents")
        else:
            # Regular user sees ONLY assigned inbound agents
            agents = db.query(Agent).join(
                UserAgent, Agent.id == UserAgent.agent_id
            ).filter(
                Agent.organization_id == uuid.UUID(organization_id),
                Agent.type == AgentType.INBOUND,
                UserAgent.user_id == uuid.UUID(user_id),
                UserAgent.is_active == True
            ).order_by(Agent.created_at.desc()).all()

            logger.info(f"User access: returning {len(agents)} assigned inbound agents")

        # Convert to response format
        agent_list = [
            InboundAgentDetails(
                id=str(agent.id),
                name=agent.name,
                language=agent.language,
                greeting=agent.opening_message,
                system_prompt=agent.system_prompt,
                voice_id=agent.voice_id,
                inbound_phone_number=agent.inbound_phone_number,
                status="active" if agent.is_active else "inactive",
                created_at=agent.created_at.isoformat(),
                capabilities=agent.capabilities
            )
            for agent in agents
        ]

        return ListInboundAgentsResponse(
            agents=agent_list,
            total=len(agent_list)
        )

    except Exception as e:
        logger.error(f"Error fetching inbound agents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch inbound agents: {str(e)}")


@router.put("/ai-call/agents/inbound/{agent_id}", response_model=UpdateInboundAgentResponse)
async def update_inbound_agent(
    agent_id: str,
    request: UpdateInboundAgentRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing inbound agent

    - **agent_name**: Name of the agent (optional)
    - **language**: Language for the agent (optional)
    - **greeting**: Greeting message (optional)
    - **ai_instructions**: System prompt for AI behavior (optional)
    - **voice_id**: Voice ID (optional)
    - **inbound_phone_number**: Phone number for receiving calls (optional)
    - **status**: Active status (optional)
    - **capabilities**: Agent capabilities (optional)
    """
    try:
        organization_id = current_user["organization_id"]
        logger.info(f"Updating inbound agent: {agent_id} for organization: {organization_id}")

        # Fetch agent from database
        agent = db.query(Agent).filter(
            Agent.id == uuid.UUID(agent_id),
            Agent.organization_id == uuid.UUID(organization_id),
            Agent.type == AgentType.INBOUND
        ).first()

        if not agent:
            raise HTTPException(status_code=404, detail="Inbound agent not found")

        # Update fields if provided
        if request.agent_name is not None:
            agent.name = request.agent_name
        if request.language is not None:
            agent.language = request.language
        if request.greeting is not None:
            agent.opening_message = request.greeting
        if request.ai_instructions is not None:
            agent.system_prompt = request.ai_instructions
        if request.voice_id is not None:
            agent.voice_id = request.voice_id
        if request.inbound_phone_number is not None:
            agent.inbound_phone_number = request.inbound_phone_number
        if request.status is not None:
            agent.is_active = request.status
        if request.capabilities is not None:
            agent.capabilities = request.capabilities

        db.commit()
        db.refresh(agent)

        logger.info(f"Inbound agent updated successfully - ID: {agent.id}")

        return UpdateInboundAgentResponse(
            id=str(agent.id),
            agent_name=agent.name,
            inbound_phone_number=agent.inbound_phone_number,
            status="active" if agent.is_active else "inactive",
            message=f"Inbound agent '{agent.name}' updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating inbound agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update inbound agent: {str(e)}")


@router.get("/ai-call/room-token", response_model=RoomTokenResponse)
async def get_room_token(
    room_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate LiveKit access token for a room

    - **room_name**: Name of the LiveKit room to join

    This endpoint allows the frontend to join a LiveKit room as an observer
    to receive real-time transcriptions from ongoing calls.
    """
    try:
        # Set token identity (use user's organization_id and a unique identifier)
        user_identity = f"observer-{current_user['organization_id']}"

        # Create video grants - observer can only receive (no publish permissions)
        video_grants = api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=False,  # Observer cannot publish audio/video
            can_subscribe=True,  # Observer can receive tracks/transcriptions
            can_publish_data=False,  # Observer cannot send data
            hidden=True,  # Observer is invisible to other participants
            recorder=True  # Mark as recorder to indicate room is being monitored
        )

        # Create access token for the room using builder pattern
        token = (
            api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
            .with_identity(user_identity)
            .with_name(f"Observer {current_user.get('email', 'User')}")
            .with_grants(video_grants)
        )

        # Generate JWT token
        jwt_token = token.to_jwt()

        logger.info(f"Generated room token for user {user_identity} to join room {room_name}")

        return RoomTokenResponse(
            token=jwt_token,
            url=settings.LIVEKIT_URL
        )

    except Exception as e:
        logger.error(f"Error generating room token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate room token: {str(e)}")


@router.post("/webhooks/livekit")
async def livekit_webhook(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    LiveKit webhook endpoint to handle room events

    Handles events like:
    - room_finished: Update call record when room closes
    - participant_left: Track participant disconnections
    """
    try:
        event_type = request.get("event")
        room_data = request.get("room", {})
        room_name = room_data.get("name")

        if not room_name:
            return {"status": "ignored", "reason": "no room name"}

        # Handle room_finished event
        if event_type == "room_finished":
            # Find the call by room_name
            call = db.query(Call).filter(Call.room_name == room_name).first()

            if call:
                # Calculate duration if started_at exists
                if call.started_at:
                    duration_seconds = int((datetime.utcnow() - call.started_at).total_seconds())
                else:
                    duration_seconds = 0

                # Update call record
                call.ended_at = datetime.utcnow()
                call.duration = duration_seconds
                call.status = "completed"

                db.commit()
                return {"status": "success", "call_id": str(call.id), "duration": duration_seconds}
            else:
                return {"status": "ignored", "reason": "call not found"}

        return {"status": "ignored", "reason": f"unhandled event type: {event_type}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/ai-call/calls/history", response_model=ListCallHistoryResponse)
async def get_call_history(
    limit: int = 50,
    offset: int = 0,
    direction: str = None,
    status: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get call history for the organization

    - **limit**: Number of records to return (default: 50)
    - **offset**: Number of records to skip (default: 0)
    - **direction**: Filter by direction (inbound/outbound)
    - **status**: Filter by status (completed/failed/no-answer)

    Returns paginated call history with agent and contact details.
    """
    try:
        organization_id = current_user["organization_id"]
        logger.info(f"Fetching call history for organization: {organization_id}")

        # Build query
        query = db.query(Call).filter(
            Call.organization_id == uuid.UUID(organization_id)
        )

        # Apply filters
        if direction:
            query = query.filter(Call.direction == direction)
        if status:
            query = query.filter(Call.status == status)

        # Get total count
        total = query.count()

        # Get paginated results, ordered by created_at descending (newest first)
        calls = query.order_by(Call.created_at.desc()).limit(limit).offset(offset).all()

        # Format response
        call_history = []
        for call in calls:
            # Get agent name
            agent_name = None
            if call.agent_id:
                agent = db.query(Agent).filter(Agent.id == call.agent_id).first()
                if agent:
                    agent_name = agent.name

            # Format datetime
            date_time = call.started_at.strftime("%m/%d/%Y, %I:%M:%S %p") if call.started_at else call.created_at.strftime("%m/%d/%Y, %I:%M:%S %p")

            call_history.append(CallHistoryItem(
                id=str(call.id),
                date_time=date_time,
                direction=call.direction.value,
                agent_name=agent_name,
                contact_name=None,  # Can be populated from lead if needed
                contact_phone=call.to_number if call.direction == CallDirection.OUTBOUND else call.from_number,
                duration=call.duration,
                status=call.status or "unknown",
                room_name=call.room_name,
                started_at=call.started_at.isoformat() if call.started_at else None,
                ended_at=call.ended_at.isoformat() if call.ended_at else None
            ))

        logger.info(f"Found {total} calls, returning {len(call_history)} records")

        return ListCallHistoryResponse(
            calls=call_history,
            total=total
        )

    except Exception as e:
        logger.error(f"Error fetching call history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch call history: {str(e)}")


# ============================================================================
# AGENT ASSIGNMENT ENDPOINTS
# ============================================================================

@router.post("/ai-call/agents/{agent_id}/assign-users", response_model=AssignmentResponse)
async def assign_agent_to_users(
    agent_id: str,
    request: AssignAgentRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Assign an agent to multiple users (Admin only)

    - **agent_id**: UUID of the agent
    - **user_ids**: List of user UUIDs to assign the agent to
    """
    try:
        # Check if current user is admin
        if current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Only admins can assign agents to users")

        organization_id = current_user["organization_id"]
        admin_user_id = current_user["sub"]  # JWT uses 'sub' for user ID

        # Fetch agent and verify it belongs to the organization
        agent = db.query(Agent).filter(
            Agent.id == uuid.UUID(agent_id),
            Agent.organization_id == uuid.UUID(organization_id)
        ).first()

        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        assigned_count = 0
        failed_count = 0
        failed_users = []

        # Process each user
        for user_id in request.user_ids:
            try:
                # Fetch user and verify they belong to the same organization
                user = db.query(User).filter(
                    User.id == uuid.UUID(user_id),
                    User.organization_id == uuid.UUID(organization_id)
                ).first()

                if not user:
                    failed_count += 1
                    failed_users.append({
                        "user_id": user_id,
                        "reason": "User not found in organization"
                    })
                    continue

                # Check if assignment already exists
                existing_assignment = db.query(UserAgent).filter(
                    UserAgent.user_id == uuid.UUID(user_id),
                    UserAgent.agent_id == uuid.UUID(agent_id)
                ).first()

                if existing_assignment:
                    if existing_assignment.is_active:
                        failed_count += 1
                        failed_users.append({
                            "user_id": user_id,
                            "reason": "Agent already assigned to this user"
                        })
                        continue
                    else:
                        # Reactivate the assignment
                        existing_assignment.is_active = True
                        existing_assignment.assigned_at = datetime.utcnow()
                        existing_assignment.assigned_by = uuid.UUID(admin_user_id)
                        assigned_count += 1
                else:
                    # Create new assignment
                    new_assignment = UserAgent(
                        user_id=uuid.UUID(user_id),
                        agent_id=uuid.UUID(agent_id),
                        assigned_by=uuid.UUID(admin_user_id),
                        is_active=True
                    )
                    db.add(new_assignment)
                    assigned_count += 1

                logger.info(f"Agent {agent_id} assigned to user {user_id} by admin {admin_user_id}")

            except Exception as e:
                failed_count += 1
                failed_users.append({
                    "user_id": user_id,
                    "reason": str(e)
                })
                logger.error(f"Error assigning agent to user {user_id}: {str(e)}")

        # Commit all successful assignments
        db.commit()

        message = f"Successfully assigned to {assigned_count} user(s)"
        if failed_count > 0:
            message += f", {failed_count} failed"

        return AssignmentResponse(
            status="success" if assigned_count > 0 else "error",
            message=message,
            assigned_count=assigned_count,
            failed_count=failed_count,
            failed_users=failed_users if failed_users else None,
            agent_id=agent_id
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error assigning agent to users: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to assign agent: {str(e)}")

@router.delete("/ai-call/agents/{agent_id}/unassign-user/{user_id}")
async def unassign_single_user_from_agent(
    agent_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Unassign a single user from an agent (Admin only)

    - **agent_id**: UUID of the agent
    - **user_id**: UUID of the user to unassign
    """
    try:
        # Check if current user is admin
        if current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Only admins can unassign users from agents")

        organization_id = current_user["organization_id"]

        # Verify agent belongs to organization
        agent = db.query(Agent).filter(
            Agent.id == uuid.UUID(agent_id),
            Agent.organization_id == uuid.UUID(organization_id)
        ).first()

        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Verify user belongs to organization
        user = db.query(User).filter(
            User.id == uuid.UUID(user_id),
            User.organization_id == uuid.UUID(organization_id)
        ).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found in organization")

        # Find and deactivate the assignment
        assignment = db.query(UserAgent).filter(
            UserAgent.agent_id == uuid.UUID(agent_id),
            UserAgent.user_id == uuid.UUID(user_id),
            UserAgent.is_active == True
        ).first()

        if not assignment:
            raise HTTPException(status_code=404, detail="User is not assigned to this agent")

        # Soft delete: mark as inactive
        assignment.is_active = False
        db.commit()

        logger.info(f"Admin {current_user['sub']} unassigned user {user_id} from agent {agent_id}")

        return {"message": f"Successfully unassigned user from agent", "status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error unassigning user from agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to unassign user: {str(e)}")


@router.get("/ai-call/agents/{agent_id}/assigned-users", response_model=ListAssignedUsersResponse)
async def get_agent_assigned_users(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all users assigned to a specific agent (Admin only)

    - **agent_id**: UUID of the agent
    """
    try:
        # Check if current user is admin
        if current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Only admins can view assigned users")

        organization_id = current_user["organization_id"]

        # Verify agent belongs to organization
        agent = db.query(Agent).filter(
            Agent.id == uuid.UUID(agent_id),
            Agent.organization_id == uuid.UUID(organization_id)
        ).first()

        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Get all active assignments for this agent
        assignments = db.query(UserAgent, User).join(
            User, UserAgent.user_id == User.id
        ).filter(
            UserAgent.agent_id == uuid.UUID(agent_id),
            UserAgent.is_active == True,
            User.organization_id == uuid.UUID(organization_id)
        ).all()

        # Build response
        assigned_users = []
        for assignment, user in assignments:
            assigned_users.append(AssignedUserDetails(
                id=str(user.id),
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.role.value,
                assigned_at=assignment.assigned_at.isoformat(),
                is_active=assignment.is_active
            ))

        return ListAssignedUsersResponse(
            users=assigned_users,
            total=len(assigned_users)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching assigned users: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch assigned users: {str(e)}")


# Health check endpoint
@router.get("/ai-call/health")
async def health_check():
    """
    Health check endpoint to verify service is running
    """
    return {
        "status": "healthy",
        "service": "ai-call-service"
    }
