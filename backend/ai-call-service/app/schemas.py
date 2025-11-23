from pydantic import BaseModel
from typing import Optional


# Trigger call request
class TriggerCallRequest(BaseModel):
    lead_id: str
    agent_id: str
    phone_number: str
    sip_trunk_id: str


# Trigger call response
class TriggerCallResponse(BaseModel):
    status: str
    room_name: str
    message: Optional[str] = None


# Trigger direct call request (no lead required)
class TriggerDirectCallRequest(BaseModel):
    agent_id: str
    phone_number: str
    sip_trunk_id: str


# Create agent request
class CreateAgentRequest(BaseModel):
    agent_name: str
    language: Optional[str] = None
    opening_message: Optional[str] = None
    ai_instructions: str
    status: bool = True
    capabilities: Optional[dict] = None


# Create agent response
class CreateAgentResponse(BaseModel):
    id: str
    agent_name: str
    status: str
    message: str


# Update agent request
class UpdateAgentRequest(BaseModel):
    agent_name: Optional[str] = None
    language: Optional[str] = None
    opening_message: Optional[str] = None
    ai_instructions: Optional[str] = None
    status: Optional[bool] = None
    capabilities: Optional[dict] = None


# Update agent response
class UpdateAgentResponse(BaseModel):
    id: str
    agent_name: str
    status: str
    message: str


# Agent details for list response
class AgentDetails(BaseModel):
    id: str
    name: str
    language: Optional[str] = None
    opening_message: Optional[str] = None
    system_prompt: Optional[str] = None
    voice_id: Optional[str] = None
    status: str
    created_at: str
    capabilities: Optional[dict] = None

    class Config:
        from_attributes = True


# List agents response
class ListAgentsResponse(BaseModel):
    agents: list[AgentDetails]
    total: int


# Room token response
class RoomTokenResponse(BaseModel):
    token: str
    url: str


# Call history item
class CallHistoryItem(BaseModel):
    id: str
    date_time: str
    direction: str
    agent_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: str
    duration: Optional[int] = None  # in seconds
    status: str
    room_name: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None

    class Config:
        from_attributes = True


# List call history response
class ListCallHistoryResponse(BaseModel):
    calls: list[CallHistoryItem]
    total: int


# Agent assignment request
class AssignAgentRequest(BaseModel):
    user_ids: list[str]  # List of user IDs to assign


# Unassign agent request
class UnassignAgentRequest(BaseModel):
    user_ids: list[str]  # List of user IDs to unassign

# Assigned user details
class AssignedUserDetails(BaseModel):
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    assigned_at: str
    is_active: bool

    class Config:
        from_attributes = True


# List assigned users response
class ListAssignedUsersResponse(BaseModel):
    users: list[AssignedUserDetails]
    total: int


# Assignment response
class AssignmentResponse(BaseModel):
    status: str
    message: str
    assigned_count: Optional[int] = None
    failed_count: Optional[int] = None
    failed_users: Optional[list[dict]] = None  # List of {user_id, reason}
    agent_id: Optional[str] = None


# Create inbound agent request
class CreateInboundAgentRequest(BaseModel):
    agent_name: str
    language: Optional[str] = None
    greeting: Optional[str] = None
    ai_instructions: str
    voice_id: Optional[str] = "shimmer"
    inbound_phone_number: str
    status: bool = True
    capabilities: Optional[dict] = None


# Create inbound agent response
class CreateInboundAgentResponse(BaseModel):
    id: str
    agent_name: str
    inbound_phone_number: str
    status: str
    message: str


# Inbound agent details for list response
class InboundAgentDetails(BaseModel):
    id: str
    name: str
    language: Optional[str] = None
    greeting: Optional[str] = None
    system_prompt: Optional[str] = None
    voice_id: Optional[str] = None
    inbound_phone_number: Optional[str] = None
    status: str
    created_at: str
    capabilities: Optional[dict] = None

    class Config:
        from_attributes = True


# List inbound agents response
class ListInboundAgentsResponse(BaseModel):
    agents: list[InboundAgentDetails]
    total: int


# Update inbound agent request
class UpdateInboundAgentRequest(BaseModel):
    agent_name: Optional[str] = None
    language: Optional[str] = None
    greeting: Optional[str] = None
    ai_instructions: Optional[str] = None
    voice_id: Optional[str] = None
    inbound_phone_number: Optional[str] = None
    status: Optional[bool] = None
    capabilities: Optional[dict] = None


# Update inbound agent response
class UpdateInboundAgentResponse(BaseModel):
    id: str
    agent_name: str
    inbound_phone_number: str
    status: str
    message: str
