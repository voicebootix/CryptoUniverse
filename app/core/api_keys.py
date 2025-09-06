"""
API Key Management and Rotation System for CryptoUniverse.

This module provides secure API key generation, validation, and rotation
with support for multiple key versions and automatic expiration.
"""

import os
import hmac
import hashlib
import secrets
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from app.core.redis import get_redis_client
from app.core.logging import logger
from app.core.config import settings

class KeyStatus(Enum):
    """Status of an API key."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ROTATED = "rotated"

class KeyVersion:
    """Represents a version of an API key with enhanced security features."""
    
    def __init__(
        self,
        key_id: str,
        prefix: str,
        secret_hash: str,
        status: KeyStatus = KeyStatus.ACTIVE,
        created_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        last_used_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        allowed_ips: Optional[List[str]] = None,
        rate_limit: Optional[int] = None,
        usage_count: int = 0,
        last_reset_at: Optional[datetime] = None
    ):
        self.key_id = key_id
        self.prefix = prefix
        self.secret_hash = secret_hash
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.expires_at = expires_at
        self.last_used_at = last_used_at
        self.metadata = metadata or {}
        self.allowed_ips = set(allowed_ips or [])
        self.rate_limit = rate_limit  # Requests per minute
        self.usage_count = usage_count
        self.last_reset_at = last_reset_at or datetime.utcnow()
    
    def is_expired(self) -> bool:
        """Check if the key has expired."""
        if self.status == KeyStatus.EXPIRED:
            return True
        if self.expires_at and datetime.utcnow() > self.expires_at:
            self.status = KeyStatus.EXPIRED
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            'key_id': self.key_id,
            'prefix': self.prefix,
            'secret_hash': self.secret_hash,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'metadata': self.metadata,
            'allowed_ips': list(self.allowed_ips) if self.allowed_ips else [],
            'rate_limit': self.rate_limit,
            'usage_count': self.usage_count,
            'last_reset_at': self.last_reset_at.isoformat() if self.last_reset_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KeyVersion':
        """Create from a dictionary."""
        return cls(
            key_id=data['key_id'],
            prefix=data['prefix'],
            secret_hash=data['secret_hash'],
            status=KeyStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']),
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
            last_used_at=datetime.fromisoformat(data['last_used_at']) if data.get('last_used_at') else None,
            metadata=data.get('metadata', {}),
            allowed_ips=data.get('allowed_ips', []),
            rate_limit=data.get('rate_limit'),
            usage_count=data.get('usage_count', 0),
            last_reset_at=datetime.fromisoformat(data['last_reset_at']) if data.get('last_reset_at') else None
        )

class APIKeyManager:
    """
    Manages API keys with support for rotation and versioning.
    
    Features:
    - Secure key generation and storage
    - Key rotation with grace periods
    - Usage tracking
    - Automatic expiration
    - Metadata storage
    """
    
    def __init__(
        self,
        redis_prefix: str = "apikey:",
        key_prefix: str = "cu_",
        key_length: int = 32,
        default_ttl_days: int = 90,
        rotation_grace_days: int = 7,
        max_versions: int = 3
    ):
        """
        Initialize the API key manager.
        
        Args:
            redis_prefix: Prefix for Redis keys
            key_prefix: Prefix for generated API keys
            key_length: Length of the secret part of the key
            default_ttl_days: Default time-to-live for new keys in days
            rotation_grace_days: Grace period after rotation before old keys are invalid
            max_versions: Maximum number of versions to keep per key
        """
        self.redis_prefix = redis_prefix
        self.key_prefix = key_prefix
        self.key_length = key_length
        self.default_ttl_days = default_ttl_days
        self.rotation_grace_days = rotation_grace_days
        self.max_versions = max_versions
    
    def _generate_key_id(self) -> str:
        """Generate a unique key ID."""
        return f"{self.key_prefix}{secrets.token_urlsafe(8)}"
    
    def _generate_secret(self) -> str:
        """Generate a secure random secret."""
        return secrets.token_urlsafe(self.key_length)
    
    def _hash_secret(self, secret: str) -> str:
        """Hash a secret for storage."""
        salt = os.urandom(16)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            secret.encode('utf-8'),
            salt,
            100000
        )
        return f"{salt.hex()}:{key.hex()}"
    
    def _verify_secret(self, secret: str, hashed_secret: str) -> bool:
        """Verify a secret against its hash."""
        try:
            salt_hex, key_hex = hashed_secret.split(':', 1)
            salt = bytes.fromhex(salt_hex)
            key = bytes.fromhex(key_hex)
            
            new_key = hashlib.pbkdf2_hmac(
                'sha256',
                secret.encode('utf-8'),
                salt,
                100000
            )
            
            return hmac.compare_digest(key, new_key)
        except (ValueError, AttributeError):
            return False
    
    async def _get_redis_key(self, key_id: str, version: Optional[int] = None) -> str:
        """Get the Redis key for a key ID and optional version."""
        if version is not None:
            return f"{self.redis_prefix}{key_id}:v{version}"
        return f"{self.redis_prefix}{key_id}"
    
    async def create_key(
        self,
        user_id: str,
        name: str,
        ttl_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """
        Create a new API key.
        
        Args:
            user_id: ID of the user creating the key
            name: Name for the key (for reference)
            ttl_days: Time-to-live in days (None for default)
            metadata: Additional metadata to store with the key
            
        Returns:
            Tuple of (key_id, secret_key)
        """
        redis = await get_redis_client()
        key_id = self._generate_key_id()
        secret_key = self._generate_secret()
        hashed_secret = self._hash_secret(secret_key)
        
        ttl_days = ttl_days or self.default_ttl_days
        expires_at = datetime.utcnow() + timedelta(days=ttl_days)
        
        key_version = KeyVersion(
            key_id=key_id,
            prefix=self.key_prefix,
            secret_hash=hashed_secret,
            status=KeyStatus.ACTIVE,
            expires_at=expires_at,
            metadata={
                'name': name,
                'user_id': user_id,
                'created_by': user_id,
                **(metadata or {})
            }
        )
        
        # Store the key in Redis
        key = await self._get_redis_key(key_id, version=1)
        await redis.set(
            key,
            json.dumps(key_version.to_dict()),
            ex=int(timedelta(days=ttl_days).total_seconds())
        )
        
        # Store the key in the user's key set
        user_keys_key = f"{self.redis_prefix}user:{user_id}:keys"
        await redis.sadd(user_keys_key, key_id)
        
        # Return the key in the format: {key_id}.{secret_key}
        return key_id, f"{key_id}.{secret_key}"
    
    async def rotate_key(
        self,
        key_id: str,
        user_id: str,
        revoke_previous: bool = True,
        ttl_days: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Rotate an API key by creating a new version and optionally revoking the old one.
        
        Args:
            key_id: The ID of the key to rotate
            user_id: ID of the user performing the rotation
            revoke_previous: Whether to revoke the previous version
            ttl_days: Time-to-live in days for the new key (None for default)
            
        Returns:
            Tuple of (success, new_secret_key)
        """
        redis = await get_redis_client()
        
        # Find the latest version of the key
        latest_version = await self._get_latest_version(key_id)
        if not latest_version:
            return False, None
        
        # Verify the user has permission to rotate this key
        if latest_version.metadata.get('user_id') != user_id:
            logger.warning(f"User {user_id} attempted to rotate key {key_id} without permission")
            return False, None
        
        # Generate a new secret
        new_secret = self._generate_secret()
        hashed_secret = self._hash_secret(new_secret)
        
        # Determine the new version number
        version = int(latest_version.key_id.split('_')[-1]) + 1 if '_' in latest_version.key_id else 2
        
        ttl_days = ttl_days or self.default_ttl_days
        expires_at = datetime.utcnow() + timedelta(days=ttl_days)
        
        # Create the new key version
        new_version = KeyVersion(
            key_id=f"{key_id}_v{version}",
            prefix=self.key_prefix,
            secret_hash=hashed_secret,
            status=KeyStatus.ACTIVE,
            expires_at=expires_at,
            metadata={
                **latest_version.metadata,
                'rotated_at': datetime.utcnow().isoformat(),
                'rotated_by': user_id,
                'previous_version': latest_version.key_id
            }
        )
        
        # Store the new version
        new_key = await self._get_redis_key(key_id, version=version)
        await redis.set(
            new_key,
            json.dumps(new_version.to_dict()),
            ex=int(timedelta(days=ttl_days).total_seconds())
        )
        
        # Update the previous version if needed
        if revoke_previous:
            latest_version.status = KeyStatus.ROTATED
            latest_version.metadata['replaced_by'] = new_version.key_id
            
            await redis.set(
                await self._get_redis_key(latest_version.key_id),
                json.dumps(latest_version.to_dict()),
                ex=self.rotation_grace_days * 24 * 3600  # Keep old keys for grace period
            )
        
        # Clean up old versions if we have too many
        await self._cleanup_old_versions(key_id)
        
        return True, f"{key_id}_v{version}.{new_secret}"
    
    async def validate_key(
        self, 
        api_key: str, 
        client_ip: Optional[str] = None,
        request_path: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate an API key with enhanced security checks.
        
        Args:
            api_key: The API key to validate in the format {key_id}.{secret}
            client_ip: The IP address of the client making the request
            request_path: The path of the request (for rate limiting)
            
        Returns:
            Tuple of (is_valid, key_info, error_message)
        """
        try:
            key_id, secret = api_key.split('.', 1)
            now = datetime.utcnow()
            
            # Find the key in Redis
            redis = await get_redis_client()
            
            # Check all versions of the key
            version = 1
            while True:
                key = await self._get_redis_key(key_id, version=version)
                key_data = await redis.get(key)
                
                if not key_data:
                    # No more versions to check
                    if version == 1:
                        # If we haven't found any versions, try without version
                        key_data = await redis.get(await self._get_redis_key(key_id))
                        if not key_data:
                            return False, {"error": "Invalid API key"}, None
                    else:
                        return False, {"error": "Invalid API key"}, None
                
                key_version = KeyVersion.from_dict(json.loads(key_data))
                
                # Check if the key is active and not expired
                if key_version.status != KeyStatus.ACTIVE:
                    version += 1
                    continue
                    
                if key_version.is_expired():
                    return False, {"error": "API key has expired"}, None
                
                # Check IP whitelist if configured
                if key_version.allowed_ips and client_ip not in key_version.allowed_ips:
                    logger.warning(f"IP {client_ip} not in allowed list for key {key_id}")
                    return False, {"error": "IP not authorized"}, None
                
                # Check rate limiting if configured
                if key_version.rate_limit:
                    # Reset counter if needed (daily)
                    if (now - key_version.last_reset_at).days >= 1:
                        key_version.usage_count = 0
                        key_version.last_reset_at = now
                    
                    # Check if rate limit exceeded
                    if key_version.usage_count >= key_version.rate_limit:
                        reset_time = (key_version.last_reset_at + timedelta(days=1)).timestamp()
                        return False, {
                            "error": "Rate limit exceeded",
                            "reset_at": int(reset_time),
                            "limit": key_version.rate_limit,
                            "remaining": 0
                        }, None
                    
                    # Increment usage counter
                    key_version.usage_count += 1
                
                # Verify the secret
                if not self._verify_secret(secret, key_version.secret_hash):
                    version += 1
                    continue
                
                # Update key usage
                key_version.last_used_at = now
                await redis.set(
                    key,
                    json.dumps(key_version.to_dict()),
                    keepttl=True  # Preserve the existing TTL
                )
                
                # Prepare response with rate limit info
                response = {
                    'key_id': key_version.key_id,
                    'user_id': key_version.metadata.get('user_id'),
                    'metadata': key_version.metadata
                }
                
                if key_version.rate_limit:
                    response.update({
                        'rate_limit': key_version.rate_limit,
                        'remaining': max(0, key_version.rate_limit - key_version.usage_count),
                        'reset_at': int((key_version.last_reset_at + timedelta(days=1)).timestamp())
                    })
                
                return True, response, None
                
                version += 1
                
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error validating API key: {e}")
            return False, {"error": "Invalid API key format"}, None
        except Exception as e:
            logger.error(f"Unexpected error validating API key: {e}")
            return False, {"error": "Internal server error"}, None
    
    async def revoke_key(self, key_id: str, user_id: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            key_id: The ID of the key to revoke
            user_id: ID of the user performing the revocation
            
        Returns:
            True if the key was revoked, False otherwise
        """
        redis = await get_redis_client()
        
        # Find the latest version of the key
        key_version = await self._get_latest_version(key_id)
        if not key_version:
            return False
        
        # Verify the user has permission to revoke this key
        if key_version.metadata.get('user_id') != user_id:
            logger.warning(f"User {user_id} attempted to revoke key {key_id} without permission")
            return False
        
        # Mark the key as revoked
        key_version.status = KeyStatus.REVOKED
        key_version.metadata['revoked_at'] = datetime.utcnow().isoformat()
        key_version.metadata['revoked_by'] = user_id
        
        # Update the key in Redis
        await redis.set(
            await self._get_redis_key(key_version.key_id),
            json.dumps(key_version.to_dict()),
            ex=30 * 24 * 3600  # Keep revoked keys for 30 days
        )
        
        return True
    
    async def list_user_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all API keys for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List of key information dictionaries
        """
        redis = await get_redis_client()
        user_keys_key = f"{self.redis_prefix}user:{user_id}:keys"
        
        # Get all key IDs for the user
        key_ids = await redis.smembers(user_keys_key)
        
        keys = []
        for key_id in key_ids:
            key_id = key_id.decode('utf-8')
            key_version = await self._get_latest_version(key_id)
            
            if key_version:
                key_info = {
                    'key_id': key_version.key_id,
                    'status': key_version.status.value,
                    'created_at': key_version.created_at.isoformat(),
                    'expires_at': key_version.expires_at.isoformat() if key_version.expires_at else None,
                    'last_used_at': key_version.last_used_at.isoformat() if key_version.last_used_at else None,
                    'metadata': key_version.metadata
                }
                keys.append(key_info)
        
        return keys
    
    async def _get_latest_version(self, key_id: str) -> Optional[KeyVersion]:
        """Get the latest version of a key."""
        redis = await get_redis_client()
        
        # Try to find the latest version
        version = 1
        latest_version = None
        
        while True:
            key = await self._get_redis_key(key_id, version=version)
            key_data = await redis.get(key)
            
            if not key_data:
                if version == 1:
                    # If we haven't found any versions, try without version
                    key_data = await redis.get(await self._get_redis_key(key_id))
                    if not key_data:
                        return None
                else:
                    break
            
            latest_version = KeyVersion.from_dict(json.loads(key_data))
            version += 1
        
        return latest_version
    
    async def _cleanup_old_versions(self, key_id: str) -> None:
        """Clean up old versions of a key."""
        redis = await get_redis_client()
        
        # Get all versions of the key
        versions = []
        version = 1
        
        while True:
            key = await self._get_redis_key(key_id, version=version)
            key_data = await redis.get(key)
            
            if not key_data:
                if version == 1:
                    # If we haven't found any versions, try without version
                    key_data = await redis.get(await self._get_redis_key(key_id))
                    if not key_data:
                        break
                else:
                    break
            
            versions.append((version, key, json.loads(key_data)))
            version += 1
        
        # Sort by version number (newest first)
        versions.sort(key=lambda x: x[0], reverse=True)
        
        # Delete old versions if we have too many
        if len(versions) > self.max_versions:
            for version, key, _ in versions[self.max_versions:]:
                await redis.delete(key)

# Global instance
api_key_manager = APIKeyManager(
    redis_prefix=f"{settings.REDIS_PREFIX}apikey:" if hasattr(settings, 'REDIS_PREFIX') else "apikey:",
    key_prefix="cu_",
    key_length=32,
    default_ttl_days=90,
    rotation_grace_days=7,
    max_versions=3
)
