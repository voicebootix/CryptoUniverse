"""
Dependencies for API key authentication.
"""

from fastapi import Depends, HTTPException, status, Security
from fastapi.security.api_key import APIKeyHeader
from typing import Optional

from app.core.api_keys import api_key_manager, KeyStatus
from app.core.logging import logger

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="API key for authentication"
)

async def get_current_user(
    api_key: Optional[str] = Security(api_key_header)
) -> dict:
    """
    Dependency to get the current user from the API key.
    
    Args:
        api_key: The API key from the request header
        
    Returns:
        User information from the API key
        
    Raises:
        HTTPException: If the API key is invalid or has insufficient permissions
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required"
        )
    
    # Validate the API key
    is_valid, key_info = await api_key_manager.validate_key(api_key)
    
    if not is_valid or not key_info:
        logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Check if the key is active
    key_status = key_info.get('status')
    if key_status != KeyStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API key is {key_status}"
        )
    
    return key_info

async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to require admin privileges.
    
    Args:
        user: The current user from get_current_user
        
    Returns:
        The user if they are an admin
        
    Raises:
        HTTPException: If the user is not an admin
    """
    if not user.get('metadata', {}).get('is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user
