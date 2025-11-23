from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import uuid


# Signup Schemas
class SignupRequestSchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    organization_name: str = Field(..., min_length=1)
    phone: Optional[str] = None

    @validator('password')
    def validate_password(cls, v):
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v


class OTPVerifySchema(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)


class SignupVerifySchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    organization_name: str = Field(..., min_length=1)
    phone: Optional[str] = None
    otp_code: str = Field(..., min_length=6, max_length=6)

    @validator('password')
    def validate_password(cls, v):
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v


class SignupResponseSchema(BaseModel):
    message: str
    email: str


# Login Schemas
class LoginRequestSchema(BaseModel):
    email: EmailStr
    password: str


class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequestSchema(BaseModel):
    refresh_token: str


# User Response Schema
class UserResponseSchema(BaseModel):
    id: uuid.UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    organization_id: uuid.UUID
    is_active: bool
    created_at: datetime
    status: Optional[str] = None  # Organization status

    class Config:
        from_attributes = True


class LoginResponseSchema(BaseModel):
    user: UserResponseSchema
    tokens: TokenResponseSchema
    # redirect_url removed - frontend handles routing with React Router


# Logout Schema
class LogoutRequestSchema(BaseModel):
    refresh_token: str


class MessageResponseSchema(BaseModel):
    message: str


# Organization Schemas
class OrganizationResponseSchema(BaseModel):
    id: uuid.UUID

    # Basic Information
    name: str
    slug: str
    legal_business_name: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None

    # Regional Settings
    timezone: str
    default_currency: str
    default_language: str

    # Billing Information
    billing_contact_name: Optional[str] = None
    billing_contact_email: Optional[str] = None
    tax_id: Optional[str] = None

    # Public Contact Information
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None

    # Business Address
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None

    # Status and metadata
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationUpdateSchema(BaseModel):
    # Basic Information
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    legal_business_name: Optional[str] = Field(None, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)

    # Regional Settings
    timezone: Optional[str] = Field(None, max_length=50)
    default_currency: Optional[str] = Field(None, max_length=10)
    default_language: Optional[str] = Field(None, max_length=10)

    # Billing Information
    billing_contact_name: Optional[str] = Field(None, max_length=255)
    billing_contact_email: Optional[EmailStr] = None
    tax_id: Optional[str] = Field(None, max_length=100)

    # Public Contact Information
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=255)

    # Business Address
    street_address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    zip_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=10)

    # Status
    status: Optional[str] = None
    is_active: Optional[bool] = None


# Forgot Password Schemas
class ForgotPasswordRequestSchema(BaseModel):
    email: EmailStr


class ResetPasswordSchema(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, description="Password must be at least 8 characters")

    @validator('new_password')
    def validate_password(cls, v):
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v


# Phone Number Schemas
class PhoneNumberCreateSchema(BaseModel):
    phone_number: str = Field(..., min_length=1, max_length=50, description="Phone number in any format")
    friendly_name: Optional[str] = Field(None, max_length=255, description="Optional friendly name")
    carrier_provider: Optional[str] = Field(None, max_length=50, description="Carrier provider (e.g., Twilio, RingCentral)")
    sip_trunk_id: Optional[str] = Field(None, max_length=100, description="SIP trunk identifier")
    assigned_to_user_id: Optional[uuid.UUID] = Field(None, description="User ID to assign this phone number")
    is_active: bool = Field(True, description="Whether the phone number is active")


class PhoneNumberUpdateSchema(BaseModel):
    phone_number: Optional[str] = Field(None, min_length=1, max_length=50, description="Phone number in any format")
    friendly_name: Optional[str] = Field(None, max_length=255, description="Optional friendly name")
    carrier_provider: Optional[str] = Field(None, max_length=50, description="Carrier provider")
    sip_trunk_id: Optional[str] = Field(None, max_length=100, description="SIP trunk identifier")
    assigned_to_user_id: Optional[uuid.UUID] = Field(None, description="User ID to assign this phone number")
    is_active: Optional[bool] = Field(None, description="Whether the phone number is active")


class PhoneNumberResponseSchema(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    phone_number: str
    friendly_name: Optional[str]
    carrier_provider: Optional[str]
    sip_trunk_id: Optional[str]
    assigned_to_user_id: Optional[uuid.UUID]
    is_active: bool
    created_at: datetime

    # Optional: Include assigned user details if needed
    assigned_user_name: Optional[str] = None

    class Config:
        from_attributes = True


# User Management Schemas
class CreateUserSchema(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone_number: Optional[str] = Field(None, max_length=50)
    role: str = Field(..., description="User role: admin or user")
    send_welcome_email: bool = Field(True, description="Send welcome email with credentials")

    @validator('role')
    def validate_role(cls, v):
        if v not in ['admin', 'user']:
            raise ValueError('Role must be either "admin" or "user"')
        return v

class CreateUserResponseSchema(BaseModel):
    id: uuid.UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    temporary_password: str
    message: str


class ListUsersResponseSchema(BaseModel):
    users: list[UserResponseSchema]
    total: int
