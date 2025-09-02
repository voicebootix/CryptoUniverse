"""
Security utilities for CryptoUniverse Enterprise.
Handles JWT token creation, validation, and encryption.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union, Tuple

import jwt
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ValidationError

from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes
REFRESH_TOKEN_EXPIRE_DAYS = 7     # 7 days
TOKEN_LEEWAY = 60                 # 60 seconds leeway for clock skew

# Token types
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


class TokenPayload(BaseModel):
    """JWT token payload structure."""
    sub: str               # Subject (user ID)
    exp: int               # Expiration time
    iat: int               # Issued at
    jti: str               # JWT ID
    type: str = TOKEN_TYPE_ACCESS  # Token type
    sid: Optional[str] = None      # Session ID
    scopes: list[str] = []         # Permission scopes
    is_admin: bool = False         # Admin flag


def generate_token_id() -> str:
    """Generate a unique token ID."""
    return str(uuid.uuid4())


def create_access_token(
    user: Any,
    session_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
    scopes: Optional[list[str]] = None,
    is_admin: bool = False
) -> Tuple[str, str]:
    """
    Create a new JWT access token with enhanced security.
    
    Args:
        user: User object with at least 'id' and 'role' attributes
        session_id: Unique session identifier
        expires_delta: Optional custom expiration time delta
        scopes: List of permission scopes
        is_admin: Whether the user is an admin
        
    Returns:
        Tuple of (token, token_id)
    """
    if not session_id:
        session_id = generate_token_id()
        
    token_id = generate_token_id()
    now = datetime.now(tz=timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    
    payload = {
        "sub": str(user.id),
        "exp": expire,
        "iat": now,
        "jti": token_id,
        "type": TOKEN_TYPE_ACCESS,
        "sid": session_id,
        "scopes": scopes or [],
        "is_admin": is_admin or user.role == "admin",
        "role": user.role
    }
    
    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=ALGORITHM
    )
    
    return token, token_id


def create_refresh_token(
    user: Any,
    session_id: Optional[str] = None
) -> Tuple[str, str]:
    """
    Create a new refresh token with enhanced security.
    
    Args:
        user: User object with at least 'id' attribute
        session_id: Unique session identifier
        
    Returns:
        Tuple of (token, token_id)
    """
    if not session_id:
        session_id = generate_token_id()
        
    token_id = generate_token_id()
    now = datetime.now(tz=timezone.utc)
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    payload = {
        "sub": str(user.id),
        "exp": expire,
        "iat": now,
        "jti": token_id,
        "type": TOKEN_TYPE_REFRESH,
        "sid": session_id
    }
    
    token = jwt.encode(
        payload,
        settings.REFRESH_TOKEN_SECRET,
        algorithm=ALGORITHM
    )
    
    return token, token_id


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash with constant-time comparison.
    
    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to verify against
        
    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        # Log the error but return False to prevent timing attacks
        import logging
        logging.warning(f"Password verification error: {str(e)}")
        # Use a dummy verify to maintain constant time
        pwd_context.verify("dummy_password", pwd_context.hash("dummy_password"))
        return False


def get_password_hash(password: str) -> str:
    """
    Generate a secure password hash.
    
    Args:
        password: The plain text password to hash
        
    Returns:
        str: The hashed password
    """
    return pwd_context.hash(password)


def verify_token(
    token: str, 
    secret_key: str, 
    token_type: Optional[str] = None,
    leeway_seconds: int = TOKEN_LEEWAY
) -> Dict[str, Any]:
    """
    Verify a JWT token with enhanced security.
    
    Args:
        token: The JWT token to verify
        secret_key: The secret key to verify the token with
        token_type: Expected token type ('access' or 'refresh')
        leeway_seconds: Leeway in seconds for clock skew
        
    Returns:
        Dict containing the decoded token payload
        
    Raises:
        JWTError: If token is invalid
    """
    try:
        # Decode token with leeway for clock skew
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[ALGORITHM],
            options={
                "verify_aud": False,
                "verify_iss": False,
                "leeway": leeway_seconds
            }
        )
        
        # Verify token type if specified
        if token_type and payload.get("type") != token_type:
            raise JWTError(f"Invalid token type: expected {token_type}")
            
        # Verify required claims
        required_claims = ["sub", "exp", "iat", "jti"]
        for claim in required_claims:
            if claim not in payload:
                raise JWTError(f"Missing required claim: {claim}")
                
        return payload
        
    except jwt.ExpiredSignatureError as e:
        raise JWTError("Token has expired") from e
    except jwt.JWTClaimsError as e:
        raise JWTError(f"Invalid token claims: {str(e)}") from e
    except Exception as e:
        raise JWTError(f"Invalid token: {str(e)}") from e


def verify_access_token(token: str) -> Dict[str, Any]:
    """
    Verify an access token.
    
    Args:
        token: The access token to verify
        
    Returns:
        Dict containing the decoded token payload
        
    Raises:
        JWTError: If token is invalid
    """
    return verify_token(
        token=token,
        secret_key=settings.SECRET_KEY,
        token_type=TOKEN_TYPE_ACCESS
    )


def verify_refresh_token(token: str) -> Dict[str, Any]:
    """
    Verify a refresh token.
    
    Args:
        token: The refresh token to verify
        
    Returns:
        Dict containing the decoded token payload
        
    Raises:
        JWTError: If token is invalid
    """
    return verify_token(
        token=token,
        secret_key=settings.REFRESH_TOKEN_SECRET,
        token_type=TOKEN_TYPE_REFRESH
    )


def is_token_revoked(token_id: str) -> bool:
    """
    Check if a token has been revoked.
    
    Args:
        token_id: The JWT ID (jti) to check
        
    Returns:
        bool: True if token is revoked, False otherwise
    """
    # This should be implemented with Redis in a real application
    # Example: return await redis.exists(f"token:revoked:{token_id}")
    return False


def revoke_token(token_id: str, expires_in: Optional[int] = None) -> None:
    """
    Revoke a token by adding it to the revocation list.
    
    Args:
        token_id: The JWT ID (jti) to revoke
        expires_in: Optional TTL in seconds for the revocation
    """
    # This should be implemented with Redis in a real application
    # Example:
    # if expires_in:
    #     await redis.setex(f"token:revoked:{token_id}", expires_in, "1")
    # else:
    #     await redis.set(f"token:revoked:{token_id}", "1")
    pass


def decode_token(token: str) -> Optional[TokenPayload]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token to decode
        
    Returns:
        Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False}
        )
        return TokenPayload(**payload)
    except (JWTError, ValidationError):
        return None


def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a refresh token and return its payload if valid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.REFRESH_TOKEN_SECRET,
            algorithms=[ALGORITHM]
        )
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None
