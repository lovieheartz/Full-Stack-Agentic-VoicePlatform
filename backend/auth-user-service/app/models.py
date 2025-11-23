from sqlalchemy import (
    Column,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    Date,
    Integer,
    Text,
    DECIMAL,
    Enum as SQLEnum,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB, ENUM as PGEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.database import Base


# Enums
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class AgentType(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallDirection(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class OrganizationStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Models
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)  # organization_name
    slug = Column(String(100), unique=True, nullable=False, index=True)
    legal_business_name = Column(String(255), nullable=True)
    industry = Column(String(100), nullable=True)
    company_size = Column(String(50), nullable=True)
    timezone = Column(String(50), default="UTC")
    default_currency = Column(String(10), default="USD")
    default_language = Column(String(10), default="en")
    billing_contact_name = Column(String(255), nullable=True)
    billing_contact_email = Column(String(255), nullable=True)
    tax_id = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)  # phone_number
    website = Column(String(255), nullable=True)
    street_address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    zip_code = Column(String(20), nullable=True)
    country = Column(String(10), nullable=True)
    # Use PostgreSQL ENUM mapped to lowercase values to match DB type `organizationstatus`
    status = Column(
        PGEnum(
            OrganizationStatus,
            name="organizationstatus",
            values_callable=lambda x: [e.value for e in x],
            create_type=False,
        ),
        default=OrganizationStatus.PENDING,
        nullable=True,
    )
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="organization")
    agents = relationship("Agent", back_populates="organization")
    phone_numbers = relationship("PhoneNumber", back_populates="organization")
    leads = relationship("Lead", back_populates="organization")
    calls = relationship("Call", back_populates="organization")
    integrations = relationship("Integration", back_populates="organization")
    campaigns = relationship("Campaign", back_populates="organization")
    model_configurations = relationship("ModelConfiguration", back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    assigned_sid = Column(String(50), nullable=True)  # Dynamic phone number assignment
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    calls = relationship("Call", back_populates="user")
    leads = relationship("Lead", back_populates="assigned_user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user")
    assigned_agents = relationship("UserAgent", foreign_keys="[UserAgent.user_id]", back_populates="user")
    campaigns = relationship("Campaign", back_populates="creator")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    jti = Column(String(255), unique=True, nullable=False, index=True)
    is_revoked = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="password_reset_tokens")


class EmailVerificationOTP(Base):
    __tablename__ = "email_verification_otps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), nullable=False, index=True)
    otp_hash = Column(String(255), nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    name = Column(String(255), nullable=False)
    type = Column(SQLEnum(AgentType), nullable=False)
    voice_provider = Column(String(50), nullable=True)
    voice_id = Column(String(255), nullable=True)
    llm_provider = Column(String(50), nullable=True)
    llm_model = Column(String(100), nullable=True)
    system_prompt = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    language = Column(String(100), nullable=True)
    opening_message = Column(Text, nullable=True)
    capabilities = Column(JSONB, nullable=True)  # Feature flags and configurations
    inbound_phone_number = Column(String(50), nullable=True)  # For inbound agents only

    # Relationships
    organization = relationship("Organization", back_populates="agents")
    calls = relationship("Call", back_populates="agent")
    assigned_users = relationship("UserAgent", back_populates="agent")
    campaigns = relationship("Campaign", back_populates="agent")


class UserAgent(Base):
    __tablename__ = "user_agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # Admin who assigned
    is_active = Column(Boolean, default=True)

    # Composite unique constraint
    __table_args__ = (
        UniqueConstraint('user_id', 'agent_id', name='unique_user_agent'),
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="assigned_agents")
    agent = relationship("Agent", back_populates="assigned_users")
    assigner = relationship("User", foreign_keys=[assigned_by])


class PhoneNumber(Base):
    __tablename__ = "phone_numbers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    phone_number = Column(String(50), unique=True, nullable=False, index=True)
    friendly_name = Column(String(255), nullable=True)
    carrier_provider = Column(String(50), nullable=True)
    sip_trunk_id = Column(String(100), nullable=True)
    assigned_to_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="phone_numbers")
    assigned_user = relationship("User")


class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True, index=True)  # Indexed for fast lookup
    company = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True)
    source = Column(String(100), nullable=True)
    assigned_to_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    crm_id = Column(String(255), nullable=True)
    extra_data = Column(
        JSONB, nullable=True
    )  # Store CRM-specific extra fields (renamed from metadata)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="leads")
    assigned_user = relationship("User", back_populates="leads")
    calls = relationship("Call", back_populates="lead")


class Call(Base):
    __tablename__ = "calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    direction = Column(SQLEnum(CallDirection), nullable=False)
    from_number = Column(String(50), nullable=True)
    to_number = Column(String(50), nullable=True)
    room_name = Column(String(255), nullable=True, index=True)  # LiveKit room identifier
    status = Column(String(50), nullable=True)
    duration = Column(Integer, nullable=True)  # Duration in seconds
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    is_recorded = Column(Boolean, default=False)
    is_transcribed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="calls")
    user = relationship("User", back_populates="calls")
    agent = relationship("Agent", back_populates="calls")
    lead = relationship("Lead", back_populates="calls")


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # carrier, crm, calendar, etc
    provider = Column(String(100), nullable=False)
    config = Column(JSONB, nullable=True)  # Encrypted configuration
    is_active = Column(Boolean, default=True)
    is_connected = Column(Boolean, default=False)
    last_sync_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="integrations")


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )  # Campaign creator
    agent_id = Column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        PGEnum(
            CampaignStatus,
            name="campaignstatus",
            values_callable=lambda x: [e.value for e in x],
            create_type=False,
        ),
        default=CampaignStatus.DRAFT,
        nullable=False,
    )
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # Optional end date
    max_call_attempts = Column(Integer, default=3, nullable=False)  # Max attempts per lead
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="campaigns")
    creator = relationship("User", back_populates="campaigns")
    agent = relationship("Agent", back_populates="campaigns")


class ModelConfiguration(Base):
    __tablename__ = "model_configurations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    name = Column(String(255), nullable=False)
    llm_provider = Column(String(50), nullable=False)
    llm_model = Column(String(100), nullable=False)
    temperature = Column(DECIMAL(3, 2), default=0.7)
    max_tokens = Column(Integer, default=1000)
    top_p = Column(DECIMAL(3, 2), default=1.0)
    frequency_penalty = Column(DECIMAL(3, 2), default=0.0)
    presence_penalty = Column(DECIMAL(3, 2), default=0.0)
    capabilities = Column(JSONB, nullable=True)  # Store additional model capabilities
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="model_configurations")


class OrganizationApprovalToken(Base):
    __tablename__ = "organization_approval_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    action = Column(String(20), nullable=False)  # 'approve' or 'decline'
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
