"""
Role and Status normalization utilities for backward compatibility.

This module handles the mapping between database stored values (uppercase)
and application/API values (lowercase) to maintain backward compatibility
with existing clients.
"""

from typing import Optional, Union
from app.models.user import UserRole, UserStatus


def normalize_role(role: Optional[Union[str, UserRole]]) -> Optional[UserRole]:
    """
    Normalize role string to UserRole enum.
    Handles both uppercase (from DB) and lowercase (from API) values.
    
    Args:
        role: Role string or UserRole enum
        
    Returns:
        UserRole enum or None if invalid
    """
    if role is None:
        return None
        
    if isinstance(role, UserRole):
        return role
        
    # Convert to string and handle both cases
    role_str = str(role).lower()
    
    # Map common variations to canonical values
    role_mapping = {
        'admin': UserRole.ADMIN,
        'trader': UserRole.TRADER,
        'viewer': UserRole.VIEWER,
        'api_only': UserRole.API_ONLY,
        # Handle uppercase from database
        'ADMIN': UserRole.ADMIN,
        'TRADER': UserRole.TRADER,
        'VIEWER': UserRole.VIEWER,
        'API_ONLY': UserRole.API_ONLY,
    }
    
    return role_mapping.get(role_str) or role_mapping.get(role)


def normalize_status(status: Optional[Union[str, UserStatus]]) -> Optional[UserStatus]:
    """
    Normalize status string to UserStatus enum.
    Handles both uppercase (from DB) and lowercase (from API) values.
    
    Args:
        status: Status string or UserStatus enum
        
    Returns:
        UserStatus enum or None if invalid
    """
    if status is None:
        return None
        
    if isinstance(status, UserStatus):
        return status
        
    # Convert to string and handle both cases
    status_str = str(status).lower()
    
    # Map common variations to canonical values
    status_mapping = {
        'active': UserStatus.ACTIVE,
        'inactive': UserStatus.INACTIVE,
        'suspended': UserStatus.SUSPENDED,
        'pending_verification': UserStatus.PENDING_VERIFICATION,
        # Handle uppercase from database
        'ACTIVE': UserStatus.ACTIVE,
        'INACTIVE': UserStatus.INACTIVE,
        'SUSPENDED': UserStatus.SUSPENDED,
        'PENDING_VERIFICATION': UserStatus.PENDING_VERIFICATION,
    }
    
    return status_mapping.get(status_str) or status_mapping.get(status)


def role_to_db_value(role: Optional[Union[str, UserRole]]) -> Optional[str]:
    """
    Convert role to database storage format (uppercase).
    
    Args:
        role: Role string or UserRole enum
        
    Returns:
        Uppercase string for database storage
    """
    normalized = normalize_role(role)
    if normalized:
        # Return uppercase for database
        return normalized.value.upper()
    return None


def status_to_db_value(status: Optional[Union[str, UserStatus]]) -> Optional[str]:
    """
    Convert status to database storage format (uppercase).
    
    Args:
        status: Status string or UserStatus enum
        
    Returns:
        Uppercase string for database storage
    """
    normalized = normalize_status(status)
    if normalized:
        # Return uppercase for database
        return normalized.value.upper()
    return None


def role_from_db(db_value: Optional[str]) -> Optional[UserRole]:
    """
    Convert database role value to UserRole enum.
    
    Args:
        db_value: Database stored role value (typically uppercase)
        
    Returns:
        UserRole enum or None
    """
    return normalize_role(db_value)


def status_from_db(db_value: Optional[str]) -> Optional[UserStatus]:
    """
    Convert database status value to UserStatus enum.
    
    Args:
        db_value: Database stored status value (typically uppercase)
        
    Returns:
        UserStatus enum or None
    """
    return normalize_status(db_value)