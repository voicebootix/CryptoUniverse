"""
SSE Authentication Dependency

Supports authentication for Server-Sent Events (SSE) endpoints.
Since EventSource doesn't support custom headers, we accept tokens via query parameter.
"""

import hashlib
from typing import Optional
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.database import get_database
from app.core.redis import get_redis_client
from app.models.user import User, UserStatus
from app.services.auth import auth_service

logger = structlog.get_logger(__name__)
security = HTTPBearer(auto_error=False)


async def get_current_user_sse(
    token: Optional[str] = Query(None, description="JWT access token for SSE authentication"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_database)
) -> User:
    """
    Get current authenticated user for SSE endpoints.
    
    Supports both:
    1. Query parameter: ?token=<jwt_token> (for EventSource/SSE)
    2. Authorization header: Bearer <jwt_token> (for regular requests)
    
    Args:
        token: JWT token from query parameter (for SSE)
        credentials: JWT token from Authorization header (for regular requests)
        db: Database session
        
    Returns:
        Authenticated User object
        
    Raises:
        HTTPException: If authentication fails
    """
    # Try to get token from query param first (SSE), then from header (regular)
    jwt_token = None
    
    if token:
        # Token from query parameter (SSE)
        jwt_token = token
        logger.debug("SSE authentication using query parameter token")
    elif credentials:
        # Token from Authorization header (regular request)
        jwt_token = credentials.credentials
        logger.debug("SSE authentication using Authorization header")
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide token via query parameter or Authorization header."
        )
    
    # Verify the JWT token
    try:
        payload = auth_service.verify_token(jwt_token)
    except Exception as e:
        logger.warning("Token verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Validate token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Access token required."
        )
    
    # Extract user ID
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Check if token is blacklisted
    redis = await get_redis_client()
    if redis:
        token_hash = hashlib.sha256(jwt_token.encode('utf-8')).hexdigest()
        blacklisted = await redis.get(f"blacklist:{token_hash}")
        if blacklisted:
            logger.info("Blacklisted token access blocked", token_hash=token_hash[:16])
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        logger.debug("Token blacklist check passed", token_hash=token

_hash[:16])
    else:
        logger.warning("Redis unavailable for blacklist check, proceeding without")
    
    # Fetch user from database
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Check user status
    if user.get_status_safe() != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active"
        )
    
    logger.debug("SSE authentication successful", user_id=str(user.id), email=user.email)
    return user
