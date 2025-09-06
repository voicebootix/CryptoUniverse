"""
API endpoints for managing API keys.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from typing import List, Optional, Set
from datetime import datetime, timedelta
from ipaddress import ip_network, ip_address

from app.core.api_keys import api_key_manager, KeyStatus
from app.api.dependencies.auth import get_current_user, require_admin
from pydantic import BaseModel, Field

router = APIRouter()

# Models
class APIKeyCreate(BaseModel):
    """Request model for creating a new API key."""
    name: str = Field(..., description="A name for the API key")
    ttl_days: Optional[int] = Field(
        None,
        description="Time-to-live in days (default: 90)",
        ge=1,
        le=365
    )
    metadata: Optional[dict] = Field(
        None,
        description="Additional metadata to store with the key"
    )
    allowed_ips: Optional[List[str]] = Field(
        None,
        description="List of allowed IP addresses or networks"
    )
    rate_limit: Optional[int] = Field(
        None,
        description="Rate limit per day"
    )
    expires_in_days: Optional[int] = Field(
        None,
        description="Key expiration in days"
    )

class APIKeyResponse(BaseModel):
    """Response model for API key operations."""
    key_id: str
    key: Optional[str] = None  # Only included on create/rotate
    status: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    metadata: dict

class APIKeyRotate(BaseModel):
    """Request model for rotating an API key."""
    revoke_previous: bool = Field(
        True,
        description="Whether to revoke the previous version of the key"
    )
    ttl_days: Optional[int] = Field(
        None,
        description="Time-to-live in days for the new key (default: same as original)",
        ge=1,
        le=365
    )

# Endpoints
@router.post(
    "/keys",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
    description="Create a new API key for the authenticated user."
)
async def create_api_key(
    request: Request,
    key_data: APIKeyCreate,
    user: dict = Depends(get_current_user)
):
    """
    Create a new API key with enhanced security features.
    
    - IP whitelisting: Restrict key usage to specific IP addresses
    - Rate limiting: Set request limits per day
    - Expiration: Optional key expiration
    """
    try:
        # Validate IP addresses if provided
        allowed_ips = set()
        if key_data.allowed_ips:
            for ip in key_data.allowed_ips:
                try:
                    # Validate IP address or network
                    if '/' in ip:
                        ip_network(ip)  # Will raise ValueError if invalid
                    else:
                        ip_address(ip)  # Will raise ValueError if invalid
                    allowed_ips.add(ip)
                except ValueError as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid IP address or network: {ip}"
                    )
        
        # Validate rate limit
        if key_data.rate_limit is not None and key_data.rate_limit <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rate limit must be a positive number"
            )
            
        # Create metadata including user ID and any additional data
        metadata = {
            'user_id': user.get('user_id'),
            'name': key_data.name,
            'created_by': user.get('user_id'),
            'client_ip': str(request.client.host) if request.client else None,
            'user_agent': request.headers.get('user-agent')
        }
        
        # Set expiration if provided
        expires_at = None
        if key_data.expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=key_data.expires_in_days)
        
        # Generate the API key with enhanced security features
        success, result = await api_key_manager.create_key(
            user_id=user.get('user_id'),
            expires_at=expires_at,
            metadata=metadata,
            allowed_ips=list(allowed_ips) if allowed_ips else None,
            rate_limit=key_data.rate_limit
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result
            )
            
        # Return the key details (the actual key is only shown once)
        key_id = result.split('.')[0]
        return {
            "key": result,  # This is the only time the full key is returned
            "key_id": key_id,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {
                **metadata,
                'allowed_ips': list(allowed_ips) if allowed_ips else None,
                'rate_limit': key_data.rate_limit
            },
            "security_notice": "Store this key securely. It will not be shown again."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating API key: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key due to an internal error"
        )

@router.get(
    "/keys",
    response_model=List[APIKeyResponse],
    summary="List API keys",
    description="List all API keys for the authenticated user."
)
async def list_api_keys(
    user: dict = Depends(get_current_user),
    admin: bool = False
):
    """
    List all API keys for the authenticated user.
    
    Admins can list all keys by setting the admin parameter to true.
    """
    user_id = user.get('user_id')
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID not found in token"
        )
    
    # If admin is requesting all keys
    is_admin = user.get('metadata', {}).get('is_admin', False)
    if admin and is_admin:
        # In a real implementation, you'd need a way to list all keys
        # This is a simplified version that only returns the current user's keys
        pass
    
    return await api_key_manager.list_user_keys(user_id)

@router.post(
    "/keys/{key_id}/rotate",
    response_model=APIKeyResponse,
    summary="Rotate an API key",
    description="Rotate an existing API key, optionally revoking the previous version."
)
async def rotate_api_key(
    key_id: str,
    rotate_data: APIKeyRotate,
    user: dict = Depends(get_current_user)
):
    """
    Rotate an API key.
    
    This will generate a new version of the key and optionally revoke the old one.
    The new key will be returned in the response and cannot be retrieved again.
    """
    user_id = user.get('user_id')
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID not found in token"
        )
    
    # Rotate the key
    success, new_key = await api_key_manager.rotate_key(
        key_id=key_id,
        user_id=user_id,
        revoke_previous=rotate_data.revoke_previous,
        ttl_days=rotate_data.ttl_days
    )
    
    if not success or not new_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to rotate key"
        )
    
    # Get the key details
    keys = await api_key_manager.list_user_keys(user_id)
    key_info = next((k for k in keys if k['key_id'].startswith(f"{key_id}_v")), None)
    
    if not key_info:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rotated key"
        )
    
    # Include the full key in the response (only time it's available)
    key_info['key'] = new_key
    
    return key_info

@router.post(
    "/keys/{key_id}/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key",
    description="Revoke an API key to prevent further use."
)
async def revoke_api_key(
    key_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Revoke an API key.
    
    This will immediately revoke the key and prevent further use.
    """
    user_id = user.get('user_id')
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID not found in token"
        )
    
    success = await api_key_manager.revoke_key(key_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to revoke key"
        )
    
    return None

@router.get(
    "/keys/{key_id}",
    response_model=APIKeyResponse,
    summary="Get API key details",
    description="Get details for a specific API key."
)
async def get_api_key(
    key_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get details for a specific API key.
    
    Users can only view their own keys unless they are an admin.
    """
    user_id = user.get('user_id')
    is_admin = user.get('metadata', {}).get('is_admin', False)
    
    # Get all keys for the user
    keys = await api_key_manager.list_user_keys(user_id)
    
    # Find the requested key
    key_info = next((k for k in keys if k['key_id'] == key_id), None)
    
    if not key_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key not found or access denied"
        )
    
    # Check if the user is the owner or an admin
    key_user_id = key_info.get('metadata', {}).get('user_id')
    if key_user_id != user_id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this key"
        )
    
    return key_info
