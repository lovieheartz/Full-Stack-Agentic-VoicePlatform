from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
import jwt
import uuid
from app.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain text password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """
    Create JWT refresh token with unique JTI
    Returns: (token, jti)
    """
    jti = str(uuid.uuid4())
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": str(user_id),
        "jti": jti,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt, jti


def decode_token(token: str) -> dict:
    """
    Decode and verify JWT token
    Raises jwt.PyJWTError if token is invalid
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


def generate_otp() -> str:
    """Generate a 6-digit OTP code"""
    import random
    return ''.join([str(random.randint(0, 9)) for _ in range(settings.OTP_LENGTH)])


def hash_otp(otp_code: str) -> str:
    """Hash OTP code for secure storage"""
    return hash_password(otp_code)


def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
    """Verify OTP against its hash"""
    return verify_password(plain_otp, hashed_otp)


def get_current_user_id_from_token(token: str) -> str:
    """
    Extract user ID from access token
    Raises ValueError if token is invalid or not an access token
    """
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise ValueError("Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise ValueError("Invalid token payload")

    return user_id
