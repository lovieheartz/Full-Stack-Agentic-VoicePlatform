from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
    Note: 'sub' contains the user_id
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
