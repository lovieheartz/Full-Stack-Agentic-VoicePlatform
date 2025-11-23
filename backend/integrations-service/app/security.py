from fastapi import HTTPException, Security, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import jwt
from app.config import settings

# HTTP Bearer scheme for JWT tokens
security_scheme = HTTPBearer()


def decode_token(token: str) -> dict:
    """
    Decode and verify JWT token
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security_scheme)) -> dict:
    """
    Dependency to get current authenticated user from JWT token
    Returns payload: {sub, email, role, organization_id, exp, iat, type}
    """
    token = credentials.credentials
    payload = decode_token(token)

    # Verify it's an access token
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    # Validate required fields exist
    if not payload.get("sub") or not payload.get("organization_id"):
        raise HTTPException(status_code=401, detail="Invalid token payload")

    return payload


async def get_current_user_flexible(
    authorization: Optional[str] = Header(None),
    x_organization_id: Optional[str] = Header(None)
) -> dict:
    """
    Flexible authentication dependency that supports two methods:
    1. JWT token in Authorization header (for user requests)
    2. Organization-ID in X-Organization-ID header (for internal service requests)

    Returns payload: {organization_id, ...} (and user info if JWT is used)
    """
    # Method 1: JWT token authentication
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]  # Remove "Bearer " prefix
        payload = decode_token(token)

        # Verify it's an access token
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")

        # Validate required fields exist
        if not payload.get("sub") or not payload.get("organization_id"):
            raise HTTPException(status_code=401, detail="Invalid token payload")

        return payload

    # Method 2: Organization-ID header (for internal service calls like MCP)
    elif x_organization_id:
        # Return minimal payload with just organization_id
        # This is sufficient for integration operations that only need org context
        return {
            "organization_id": x_organization_id,
            "sub": None,  # No user context for service-to-service calls
            "email": None,
            "role": None,
            "type": "service"  # Mark as service token
        }

    # No authentication provided
    else:
        raise HTTPException(status_code=401, detail="Authentication required: provide either JWT token or X-Organization-ID header")
