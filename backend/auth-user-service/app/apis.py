from fastapi import APIRouter, Depends, HTTPException, status, Header, Response, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from app.database import get_db
from app import models, schemas, security
from app.utils import (
    send_otp_email,
    send_welcome_email,
    send_reset_password_email,
    send_admin_organization_notification,
    send_organization_approved_email,
    send_organization_declined_email,
    send_user_credentials_email,
)
from app.config import settings
import uuid

router = APIRouter()


# Dependency to get current user from Authorization header
def get_current_user(
    authorization: Optional[str] = Header(None), db: Session = Depends(get_db)
) -> models.User:
    """
    Dependency to extract and validate current user from access token
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    token = parts[1]

    try:
        user_id = security.get_current_user_id_from_token(token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    # Get user from database
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    return user


@router.post(
    "/auth/signup/request",
    response_model=schemas.SignupResponseSchema,
    responses={
        200: {"description": "OTP sent successfully"},
        400: {"description": "Email already registered"},
        500: {"description": "Failed to send email (SMTP error)"},
    },
)
def request_signup_otp(
    request: schemas.SignupRequestSchema, db: Session = Depends(get_db)
):
    """
    Step 1: Request OTP for email verification
    Sends a 6-digit OTP code to the user's email
    """
    # Check if email already exists
    existing_user = (
        db.query(models.User).filter(models.User.email == request.email).first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Generate OTP
    otp_code = security.generate_otp()
    otp_hash = security.hash_otp(otp_code)

    # Delete any existing OTPs for this email
    db.query(models.EmailVerificationOTP).filter(
        models.EmailVerificationOTP.email == request.email
    ).delete()

    # Store OTP in database
    otp_record = models.EmailVerificationOTP(
        email=request.email,
        otp_hash=otp_hash,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )
    db.add(otp_record)
    db.commit()

    # Send OTP via email
    email_sent = send_otp_email(request.email, otp_code)
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP email. Please check SMTP configuration.",
        )

    return schemas.SignupResponseSchema(
        message="OTP sent to your email. Please verify within 10 minutes.",
        email=request.email,
    )


@router.post(
    "/auth/signup/verify",
    response_model=schemas.LoginResponseSchema,
    responses={
        200: {"description": "User created successfully, returns tokens"},
        400: {"description": "Invalid OTP, expired OTP, or email already registered"},
    },
)
def verify_signup_otp(
    request: schemas.SignupVerifySchema, db: Session = Depends(get_db)
):
    """
    Step 2: Verify OTP and create user account
    Creates organization and user, returns JWT tokens
    """
    # Get OTP record
    otp_record = (
        db.query(models.EmailVerificationOTP)
        .filter(
            models.EmailVerificationOTP.email == request.email,
            models.EmailVerificationOTP.is_used == False,
        )
        .first()
    )

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP"
        )

    # Check expiration
    if datetime.utcnow() > otp_record.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one.",
        )

    # Verify OTP
    if not security.verify_otp(request.otp_code, otp_record.otp_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP code"
        )

    # Mark OTP as used
    otp_record.is_used = True
    db.commit()

    # Check if email already exists (double check)
    existing_user = (
        db.query(models.User).filter(models.User.email == request.email).first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create organization
    org_slug = request.organization_name.lower().replace(" ", "-")
    # Make slug unique
    base_slug = org_slug
    counter = 1
    while (
        db.query(models.Organization)
        .filter(models.Organization.slug == org_slug)
        .first()
    ):
        org_slug = f"{base_slug}-{counter}"
        counter += 1

    organization = models.Organization(
        name=request.organization_name,
        slug=org_slug,
        email=request.email,
        phone=request.phone,
        status=models.OrganizationStatus.PENDING,  # Set as pending - requires admin approval
    )
    db.add(organization)
    db.flush()

    # Create user with ADMIN role (first user in organization)
    user = models.User(
        organization_id=organization.id,
        email=request.email,
        password_hash=security.hash_password(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        role=models.UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Send welcome email
    send_welcome_email(user.email, user.first_name)

    # Generate tokens
    access_token = security.create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "organization_id": str(user.organization_id),
        }
    )

    refresh_token, jti = security.create_refresh_token(str(user.id))

    # Store refresh token in database
    refresh_token_record = models.RefreshToken(
        user_id=user.id,
        token_hash=security.hash_password(refresh_token),
        jti=jti,
        expires_at=datetime.utcnow()
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_token_record)
    db.commit()

    # Prepare user response with organization status
    user_response = schemas.UserResponseSchema.from_orm(user)
    user_response.status = organization.status.value

    # Frontend handles all routing with React Router based on user.status and user.role
    return schemas.LoginResponseSchema(
        user=user_response,
        tokens=schemas.TokenResponseSchema(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )


@router.post(
    "/auth/login",
    response_model=schemas.LoginResponseSchema,
    responses={
        200: {"description": "Login successful, returns tokens"},
        401: {"description": "Incorrect email or password"},
        403: {"description": "Account is inactive"},
    },
)
def login(request: schemas.LoginRequestSchema, db: Session = Depends(get_db)):
    """
    Login endpoint
    Verifies credentials and returns JWT tokens
    """
    # Find user by email
    user = db.query(models.User).filter(models.User.email == request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Verify password
    if not security.verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support.",
        )

    # Fetch organization to get status
    organization = (
        db.query(models.Organization)
        .filter(models.Organization.id == user.organization_id)
        .first()
    )

    # Role-based organization status check
    # ADMIN: Can login with any status (PENDING → onboarding, ACTIVE → admin panel)
    # USER: Can only login if organization is ACTIVE
    if user.role == models.UserRole.USER:
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization not found.",
            )

        if organization.status != models.OrganizationStatus.ACTIVE:
            status_msg = {
                models.OrganizationStatus.PENDING: "pending approval",
                models.OrganizationStatus.SUSPENDED: "suspended",
                models.OrganizationStatus.CANCELLED: "cancelled",
            }.get(organization.status, "inactive")

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your organization is {status_msg}. Please wait for your organization to be activated.",
            )

    # Generate tokens
    access_token = security.create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "organization_id": str(user.organization_id),
        }
    )

    refresh_token, jti = security.create_refresh_token(str(user.id))

    # Store refresh token in database
    refresh_token_record = models.RefreshToken(
        user_id=user.id,
        token_hash=security.hash_password(refresh_token),
        jti=jti,
        expires_at=datetime.utcnow()
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_token_record)
    db.commit()

    # Prepare user response with organization status
    user_response = schemas.UserResponseSchema.from_orm(user)
    user_response.status = organization.status.value if organization else None

    # Frontend handles all routing with React Router based on user.status and user.role
    return schemas.LoginResponseSchema(
        user=user_response,
        tokens=schemas.TokenResponseSchema(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )


@router.post(
    "/auth/refresh",
    response_model=schemas.TokenResponseSchema,
    responses={
        200: {"description": "Token refreshed successfully"},
        401: {"description": "Invalid or revoked refresh token, or user not found"},
    },
)
def refresh_token(
    request: schemas.RefreshTokenRequestSchema, db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    Implements rotating refresh tokens for security
    """
    try:
        # Decode refresh token
        payload = security.decode_token(request.refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )

        user_id = payload.get("sub")
        jti = payload.get("jti")

        # Verify refresh token exists in database and is not revoked
        token_record = (
            db.query(models.RefreshToken)
            .filter(
                models.RefreshToken.jti == jti, models.RefreshToken.is_revoked == False
            )
            .first()
        )

        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked refresh token",
            )

        # Revoke old refresh token (rotating tokens)
        token_record.is_revoked = True
        db.commit()

        # Get user
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Generate new tokens
        access_token = security.create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "role": user.role.value,
                "organization_id": str(user.organization_id),
            }
        )

        new_refresh_token, new_jti = security.create_refresh_token(str(user.id))

        # Store new refresh token
        new_token_record = models.RefreshToken(
            user_id=user.id,
            token_hash=security.hash_password(new_refresh_token),
            jti=new_jti,
            expires_at=datetime.utcnow()
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(new_token_record)
        db.commit()

        return schemas.TokenResponseSchema(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post(
    "/auth/logout",
    response_model=schemas.MessageResponseSchema,
    responses={
        200: {"description": "Successfully logged out"},
    },
)
def logout(request: schemas.LogoutRequestSchema, db: Session = Depends(get_db)):
    """
    Logout endpoint
    Revokes the refresh token
    """
    try:
        # Decode refresh token
        payload = security.decode_token(request.refresh_token)
        jti = payload.get("jti")

        # Revoke refresh token
        token_record = (
            db.query(models.RefreshToken).filter(models.RefreshToken.jti == jti).first()
        )

        if token_record:
            token_record.is_revoked = True
            db.commit()

        return schemas.MessageResponseSchema(message="Successfully logged out")

    except ValueError:
        # Even if token is invalid, return success for logout
        return schemas.MessageResponseSchema(message="Successfully logged out")


@router.post(
    "/auth/forgot-password",
    response_model=schemas.MessageResponseSchema,
    responses={
        200: {"description": "Password reset OTP sent"},
        404: {"description": "User not found"},
        500: {"description": "Failed to send email"},
    },
)
def forgot_password(
    request: schemas.ForgotPasswordRequestSchema, db: Session = Depends(get_db)
):
    """
    Request password reset
    Sends a 6-digit OTP code to user's email
    """
    # Find user by email
    user = db.query(models.User).filter(models.User.email == request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email not found",
        )

    # Generate 6-digit OTP
    import random

    otp_code = "".join([str(random.randint(0, 9)) for _ in range(6)])
    otp_hash = security.hash_password(otp_code)

    # Delete any existing reset tokens for this user
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.id,
        models.PasswordResetToken.is_used == False,
    ).delete()

    # Create new reset OTP token (expires in OTP_EXPIRE_MINUTES)
    reset_token_record = models.PasswordResetToken(
        user_id=user.id,
        token_hash=otp_hash,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )
    db.add(reset_token_record)
    db.commit()

    # Send reset email with OTP
    email_sent = send_reset_password_email(user.email, otp_code)
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send password reset email",
        )

    return schemas.MessageResponseSchema(
        message="Password reset code sent to your email"
    )


@router.post(
    "/auth/reset-password",
    response_model=schemas.MessageResponseSchema,
    responses={
        200: {"description": "Password reset successfully"},
        400: {"description": "Invalid or expired OTP code"},
        404: {"description": "User not found"},
    },
)
def reset_password(request: schemas.ResetPasswordSchema, db: Session = Depends(get_db)):
    """
    Reset password using OTP code
    """
    # Find user by email
    user = db.query(models.User).filter(models.User.email == request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Find valid reset OTP
    reset_token_record = (
        db.query(models.PasswordResetToken)
        .filter(
            models.PasswordResetToken.user_id == user.id,
            models.PasswordResetToken.is_used == False,
        )
        .first()
    )

    if not reset_token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP code",
        )

    # Check expiration
    if datetime.utcnow() > reset_token_record.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP code has expired. Please request a new one.",
        )

    # Verify OTP code
    if not security.verify_password(request.otp_code, reset_token_record.token_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP code"
        )

    # Update password
    user.password_hash = security.hash_password(request.new_password)

    # Mark OTP as used
    reset_token_record.is_used = True

    db.commit()

    return schemas.MessageResponseSchema(
        message="Password reset successfully. You can now login with your new password."
    )


# Organization endpoints
@router.get(
    "/organization",
    response_model=schemas.OrganizationResponseSchema,
    responses={
        200: {"description": "Organization details retrieved successfully"},
        401: {"description": "Unauthorized - Invalid or missing token"},
        403: {"description": "Forbidden - User account is inactive"},
        404: {"description": "Organization not found"},
    },
)
def get_organization(
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get current user's organization details
    Requires: Authorization Bearer token
    """
    organization = (
        db.query(models.Organization)
        .filter(models.Organization.id == current_user.organization_id)
        .first()
    )

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    return schemas.OrganizationResponseSchema.model_validate(organization)


@router.patch(
    "/organization",
    response_model=schemas.OrganizationResponseSchema,
    responses={
        200: {"description": "Organization updated successfully"},
        401: {"description": "Unauthorized - Invalid or missing token"},
        403: {"description": "Forbidden - Only administrators can update organization"},
        404: {"description": "Organization not found"},
    },
)
def update_organization(
    update_data: schemas.OrganizationUpdateSchema,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update organization details
    Requires: Authorization Bearer token
    Only users with ADMIN role can update organization
    """
    # Check if user is admin
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update organization details",
        )

    # Get organization
    organization = (
        db.query(models.Organization)
        .filter(models.Organization.id == current_user.organization_id)
        .first()
    )

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    # Check if this is first-time onboarding (organization has minimal data)
    is_onboarding = (
        organization.name
        and not organization.industry
        and not organization.legal_business_name
    )

    # Update only provided fields
    update_dict = update_data.model_dump(exclude_unset=True)

    # If name is being updated, regenerate slug
    if "name" in update_dict and update_dict["name"]:
        new_slug = update_dict["name"].lower().replace(" ", "-")
        base_slug = new_slug
        counter = 1

        # Make slug unique (skip current organization)
        while (
            db.query(models.Organization)
            .filter(
                models.Organization.slug == new_slug,
                models.Organization.id != organization.id,
            )
            .first()
        ):
            new_slug = f"{base_slug}-{counter}"
            counter += 1

        organization.slug = new_slug

    # Update fields
    for field, value in update_dict.items():
        if hasattr(organization, field):
            setattr(organization, field, value)

    # Check if organization profile is complete for admin notification
    has_complete_profile = (
        organization.name
        and organization.industry
        and (organization.email or organization.phone)
    )

    db.commit()
    db.refresh(organization)

    # Send admin notification email if organization profile is complete and status is PENDING
    if has_complete_profile and organization.status == models.OrganizationStatus.PENDING:
        try:
            # Generate secure tokens for approve/decline actions (valid for 7 days)
            import secrets

            approval_token_raw = secrets.token_urlsafe(32)
            decline_token_raw = secrets.token_urlsafe(32)

            approval_token_hash = security.hash_password(approval_token_raw)
            decline_token_hash = security.hash_password(decline_token_raw)

            # Delete any existing unused tokens for this organization
            db.query(models.OrganizationApprovalToken).filter(
                models.OrganizationApprovalToken.organization_id == organization.id,
                models.OrganizationApprovalToken.is_used == False,
            ).delete()

            # Store tokens in database
            approval_token_record = models.OrganizationApprovalToken(
                organization_id=organization.id,
                action="approve",
                token_hash=approval_token_hash,
                expires_at=datetime.utcnow() + timedelta(days=7),
            )
            decline_token_record = models.OrganizationApprovalToken(
                organization_id=organization.id,
                action="decline",
                token_hash=decline_token_hash,
                expires_at=datetime.utcnow() + timedelta(days=7),
            )
            db.add(approval_token_record)
            db.add(decline_token_record)
            db.commit()

            # Prepare organization and user data for email
            org_data = {
                "id": str(organization.id),
                "name": organization.name,
                "legal_business_name": organization.legal_business_name,
                "industry": organization.industry,
                "email": organization.email,
                "phone": organization.phone,
                "website": organization.website,
                "timezone": organization.timezone,
                "default_currency": organization.default_currency,
            }

            user_data = {
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "email": current_user.email,
                "role": current_user.role.value,
            }

            # Send admin notification
            send_admin_organization_notification(
                organization_data=org_data,
                user_data=user_data,
                approval_token=approval_token_raw,
                decline_token=decline_token_raw,
            )
        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to send admin notification email: {str(e)}")

    return schemas.OrganizationResponseSchema.model_validate(organization)


@router.get(
    "/organization/approve",
    response_model=schemas.MessageResponseSchema,
    responses={
        200: {"description": "Organization approved successfully"},
        400: {"description": "Invalid or expired token"},
        404: {"description": "Organization not found"},
    },
)
def approve_organization(
    token: str,
    silent: bool = Query(
        False, description="If true, return 204 with no body for email button clicks."
    ),
    db: Session = Depends(get_db),
):
    """
    Approve an organization using the approval token from email
    This endpoint is called when admin clicks the "Approve" button in the email
    """
    # Find all approval tokens that haven't been used
    approval_tokens = (
        db.query(models.OrganizationApprovalToken)
        .filter(
            models.OrganizationApprovalToken.action == "approve",
            models.OrganizationApprovalToken.is_used == False,
        )
        .all()
    )

    # Find matching token
    token_record = None
    for t in approval_tokens:
        if security.verify_password(token, t.token_hash):
            token_record = t
            break

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired approval token",
        )

    # Check expiration
    if datetime.utcnow() > token_record.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Approval token has expired"
        )

    # Get organization
    organization = (
        db.query(models.Organization)
        .filter(models.Organization.id == token_record.organization_id)
        .first()
    )

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    # Get the admin user for this organization
    admin_user = (
        db.query(models.User)
        .filter(
            models.User.organization_id == organization.id,
            models.User.role == models.UserRole.ADMIN,
        )
        .first()
    )

    # Update organization status to ACTIVE
    organization.status = models.OrganizationStatus.ACTIVE
    organization.is_active = True

    # Activate all users in this organization
    db.query(models.User).filter(models.User.organization_id == organization.id).update(
        {"is_active": True}
    )

    # Mark all tokens for this organization as used
    db.query(models.OrganizationApprovalToken).filter(
        models.OrganizationApprovalToken.organization_id == organization.id,
        models.OrganizationApprovalToken.is_used == False,
    ).update({"is_used": True})

    db.commit()

    # Send approval email to user
    if admin_user:
        try:
            send_organization_approved_email(
                email=admin_user.email,
                first_name=admin_user.first_name or "User",
                organization_name=organization.name,
            )
        except Exception as e:
            print(f"Failed to send approval email to user: {str(e)}")

    if silent:
        return Response(status_code=204)

    return schemas.MessageResponseSchema(
        message=f"Organization '{organization.name}' has been approved successfully. User notified via email."
    )


@router.get(
    "/organization/decline",
    response_model=schemas.MessageResponseSchema,
    responses={
        200: {"description": "Organization declined successfully"},
        400: {"description": "Invalid or expired token"},
        404: {"description": "Organization not found"},
    },
)
def decline_organization(
    token: str,
    reason: Optional[str] = None,
    silent: bool = Query(
        False, description="If true, return 204 with no body for email button clicks."
    ),
    db: Session = Depends(get_db),
):
    """
    Decline an organization using the decline token from email
    This endpoint is called when admin clicks the "Decline" button in the email
    Optional reason parameter can be provided for transparency
    """
    # Find all decline tokens that haven't been used
    decline_tokens = (
        db.query(models.OrganizationApprovalToken)
        .filter(
            models.OrganizationApprovalToken.action == "decline",
            models.OrganizationApprovalToken.is_used == False,
        )
        .all()
    )

    # Find matching token
    token_record = None
    for t in decline_tokens:
        if security.verify_password(token, t.token_hash):
            token_record = t
            break

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired decline token",
        )

    # Check expiration
    if datetime.utcnow() > token_record.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Decline token has expired"
        )

    # Get organization
    organization = (
        db.query(models.Organization)
        .filter(models.Organization.id == token_record.organization_id)
        .first()
    )

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    # Get the admin user for this organization
    admin_user = (
        db.query(models.User)
        .filter(
            models.User.organization_id == organization.id,
            models.User.role == models.UserRole.ADMIN,
        )
        .first()
    )

    # Update organization status to CANCELLED
    organization.status = models.OrganizationStatus.CANCELLED
    organization.is_active = False

    # Deactivate all users in this organization
    db.query(models.User).filter(models.User.organization_id == organization.id).update(
        {"is_active": False}
    )

    # Mark all tokens for this organization as used
    db.query(models.OrganizationApprovalToken).filter(
        models.OrganizationApprovalToken.organization_id == organization.id,
        models.OrganizationApprovalToken.is_used == False,
    ).update({"is_used": True})

    db.commit()

    # Send decline email to user
    if admin_user:
        try:
            send_organization_declined_email(
                email=admin_user.email,
                first_name=admin_user.first_name or "User",
                organization_name=organization.name,
                reason=reason,
            )
        except Exception as e:
            print(f"Failed to send decline email to user: {str(e)}")

    if silent:
        return Response(status_code=204)

    return schemas.MessageResponseSchema(
        message=f"Organization '{organization.name}' has been declined. User notified via email."
    )


# Phone Number Endpoints
@router.get(
    "/auth/phone-numbers",
    response_model=list[schemas.PhoneNumberResponseSchema],
    responses={
        200: {"description": "List of phone numbers retrieved successfully"},
        401: {"description": "Unauthorized - Invalid or missing token"},
        403: {"description": "Forbidden - User account is inactive"},
    },
)
def get_phone_numbers(
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get all phone numbers for the current user's organization
    Requires: Authorization Bearer token
    """
    # Query phone numbers for the user's organization
    phone_numbers = (
        db.query(models.PhoneNumber)
        .filter(models.PhoneNumber.organization_id == current_user.organization_id)
        .order_by(models.PhoneNumber.created_at.desc())
        .all()
    )

    # Prepare response with assigned user names
    response_list = []
    for phone_number in phone_numbers:
        phone_response = schemas.PhoneNumberResponseSchema.from_orm(phone_number)

        # Add assigned user name if available
        if phone_number.assigned_to_user_id:
            assigned_user = (
                db.query(models.User)
                .filter(models.User.id == phone_number.assigned_to_user_id)
                .first()
            )
            if assigned_user:
                phone_response.assigned_user_name = (
                    f"{assigned_user.first_name} {assigned_user.last_name}".strip()
                    or assigned_user.email
                )

        response_list.append(phone_response)

    return response_list


@router.post(
    "/auth/phone-numbers",
    response_model=schemas.PhoneNumberResponseSchema,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Phone number created successfully"},
        400: {"description": "Phone number already exists"},
        401: {"description": "Unauthorized - Invalid or missing token"},
        403: {"description": "Forbidden - Only administrators can create phone numbers"},
    },
)
def create_phone_number(
    phone_data: schemas.PhoneNumberCreateSchema,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new phone number for the organization
    Requires: Authorization Bearer token
    Only users with ADMIN role can create phone numbers
    """
    # Check if user is admin
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create phone numbers",
        )

    # Check if phone number already exists
    existing_phone = (
        db.query(models.PhoneNumber)
        .filter(models.PhoneNumber.phone_number == phone_data.phone_number)
        .first()
    )
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already exists",
        )

    # If assigned_to_user_id is provided, verify the user exists and belongs to the same organization
    if phone_data.assigned_to_user_id:
        assigned_user = (
            db.query(models.User)
            .filter(
                models.User.id == phone_data.assigned_to_user_id,
                models.User.organization_id == current_user.organization_id,
            )
            .first()
        )
        if not assigned_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user not found or does not belong to your organization",
            )

    # Create new phone number
    new_phone_number = models.PhoneNumber(
        organization_id=current_user.organization_id,
        phone_number=phone_data.phone_number,
        friendly_name=phone_data.friendly_name,
        carrier_provider=phone_data.carrier_provider,
        sip_trunk_id=phone_data.sip_trunk_id,
        assigned_to_user_id=phone_data.assigned_to_user_id,
        is_active=phone_data.is_active,
    )

    db.add(new_phone_number)
    db.commit()
    db.refresh(new_phone_number)

    # Prepare response with assigned user name
    phone_response = schemas.PhoneNumberResponseSchema.from_orm(new_phone_number)
    if new_phone_number.assigned_to_user_id:
        assigned_user = (
            db.query(models.User)
            .filter(models.User.id == new_phone_number.assigned_to_user_id)
            .first()
        )
        if assigned_user:
            phone_response.assigned_user_name = (
                f"{assigned_user.first_name} {assigned_user.last_name}".strip()
                or assigned_user.email
            )

    return phone_response


@router.put(
    "/auth/phone-numbers/{phone_number_id}",
    response_model=schemas.PhoneNumberResponseSchema,
    responses={
        200: {"description": "Phone number updated successfully"},
        400: {"description": "Phone number already exists (if phone_number is being updated)"},
        401: {"description": "Unauthorized - Invalid or missing token"},
        403: {"description": "Forbidden - Only administrators can update phone numbers"},
        404: {"description": "Phone number not found"},
    },
)
def update_phone_number(
    phone_number_id: uuid.UUID,
    phone_data: schemas.PhoneNumberUpdateSchema,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing phone number
    Requires: Authorization Bearer token
    Only users with ADMIN role can update phone numbers
    """
    # Check if user is admin
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update phone numbers",
        )

    # Get the phone number
    phone_number = (
        db.query(models.PhoneNumber)
        .filter(
            models.PhoneNumber.id == phone_number_id,
            models.PhoneNumber.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not phone_number:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not found",
        )

    # Update only provided fields
    update_dict = phone_data.model_dump(exclude_unset=True)

    # If phone number is being updated, check for duplicates
    if "phone_number" in update_dict and update_dict["phone_number"]:
        existing_phone = (
            db.query(models.PhoneNumber)
            .filter(
                models.PhoneNumber.phone_number == update_dict["phone_number"],
                models.PhoneNumber.id != phone_number_id,
            )
            .first()
        )
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already exists",
            )

    # If assigned_to_user_id is being updated, verify the user exists and belongs to the same organization
    if "assigned_to_user_id" in update_dict and update_dict["assigned_to_user_id"]:
        assigned_user = (
            db.query(models.User)
            .filter(
                models.User.id == update_dict["assigned_to_user_id"],
                models.User.organization_id == current_user.organization_id,
            )
            .first()
        )
        if not assigned_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user not found or does not belong to your organization",
            )

    # Update fields
    for field, value in update_dict.items():
        if hasattr(phone_number, field):
            setattr(phone_number, field, value)

    db.commit()
    db.refresh(phone_number)

    # Prepare response with assigned user name
    phone_response = schemas.PhoneNumberResponseSchema.from_orm(phone_number)
    if phone_number.assigned_to_user_id:
        assigned_user = (
            db.query(models.User)
            .filter(models.User.id == phone_number.assigned_to_user_id)
            .first()
        )
        if assigned_user:
            phone_response.assigned_user_name = (
                f"{assigned_user.first_name} {assigned_user.last_name}".strip()
                or assigned_user.email
            )

    return phone_response


@router.delete(
    "/auth/phone-numbers/{phone_number_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Phone number deleted successfully"},
        401: {"description": "Unauthorized - Invalid or missing token"},
        403: {"description": "Forbidden - Only administrators can delete phone numbers"},
        404: {"description": "Phone number not found"},
    },
)
def delete_phone_number(
    phone_number_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a phone number
    Requires: Authorization Bearer token
    Only users with ADMIN role can delete phone numbers
    """
    # Check if user is admin
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete phone numbers",
        )

    # Get the phone number
    phone_number = (
        db.query(models.PhoneNumber)
        .filter(
            models.PhoneNumber.id == phone_number_id,
            models.PhoneNumber.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not phone_number:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not found",
        )

    # Delete the phone number
    db.delete(phone_number)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# User Management Endpoints
@router.post(
    "/auth/users",
    response_model=schemas.CreateUserResponseSchema,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Email already exists"},
        401: {"description": "Unauthorized - Invalid or missing token"},
        403: {"description": "Forbidden - Only administrators can create users"},
    },
)
def create_user(
    user_data: schemas.CreateUserSchema,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new user in the organization
    Requires: Authorization Bearer token
    Only users with ADMIN role can create users
    Admin will set the password and it will be sent via email
    """
    # Check if user is admin
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create users",
        )

    # Check if email already exists
    existing_user = (
        db.query(models.User).filter(models.User.email == user_data.email).first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Generate random 8-character temporary password with uppercase, lowercase, and digits
    import random
    import string

    # Ensure password has at least: 1 uppercase, 1 lowercase, 1 digit
    temp_password = (
        random.choice(string.ascii_uppercase)
        + random.choice(string.ascii_lowercase)
        + random.choice(string.digits)
        + "".join(
            random.choices(
                string.ascii_uppercase + string.ascii_lowercase + string.digits, k=5
            )
        )
    )
    # Shuffle to make it random
    temp_password_list = list(temp_password)
    random.shuffle(temp_password_list)
    temp_password = "".join(temp_password_list)

    # Create new user with the same organization as the admin
    new_user = models.User(
        organization_id=current_user.organization_id,
        email=user_data.email,
        password_hash=security.hash_password(temp_password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=models.UserRole.ADMIN if user_data.role == "admin" else models.UserRole.USER,
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Send credentials email if requested
    email_sent = False
    if user_data.send_welcome_email:
        email_sent = send_user_credentials_email(
            email=new_user.email,
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            temp_password=temp_password,
        )

    # Prepare response message
    message = "User created successfully."
    if user_data.send_welcome_email:
        if email_sent:
            message += " Credentials have been sent to the user's email."
        else:
            message += " However, failed to send credentials email. Please share the temporary password manually."

    return schemas.CreateUserResponseSchema(
        id=new_user.id,
        email=new_user.email,
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        role=new_user.role.value,
        temporary_password=temp_password,
        message=message,
    )


@router.get(
    "/auth/users",
    response_model=schemas.ListUsersResponseSchema,
    responses={
        200: {"description": "List of users retrieved successfully"},
        401: {"description": "Unauthorized - Invalid or missing token"},
        403: {"description": "Forbidden - Only administrators can list users"},
    },
)
def list_users(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all users in the current user's organization
    Requires: Authorization Bearer token
    Only users with ADMIN role can list users
    """
    # Check if user is admin
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can list users",
        )

    # Query all users in the same organization
    users = (
        db.query(models.User)
        .filter(models.User.organization_id == current_user.organization_id)
        .order_by(models.User.created_at.desc())
        .all()
    )

    # Convert to response schema
    user_responses = [schemas.UserResponseSchema.from_orm(user) for user in users]

    return schemas.ListUsersResponseSchema(
        users=user_responses,
        total=len(user_responses),
    )


@router.get(
    "/user/profile",
    response_model=schemas.UserResponseSchema,
    responses={
        200: {"description": "Current user profile retrieved successfully"},
        401: {"description": "Unauthorized - Invalid or missing token"},
        403: {"description": "Forbidden - User account is inactive"},
    },
)
def get_current_user_profile(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current authenticated user's profile details
    Requires: Authorization Bearer token
    """
    # Get organization status for the response
    organization = (
        db.query(models.Organization)
        .filter(models.Organization.id == current_user.organization_id)
        .first()
    )

    # Prepare user response with organization status
    user_response = schemas.UserResponseSchema.from_orm(current_user)
    user_response.status = organization.status.value if organization else None

    return user_response


# Health check endpoint
@router.get(
    "/health",
    responses={
        200: {"description": "Service is healthy"},
    },
)
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "auth-user-service"}

