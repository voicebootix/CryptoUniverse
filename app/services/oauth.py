"""
OAuth Service for Social Authentication

Handles OAuth flows for Google, GitHub, and other providers.
Manages user authentication, account linking, and token management.
"""

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode

import httpx
import structlog
import jwt
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user import User, UserRole, UserStatus
from app.models.oauth import UserOAuthConnection, OAuthState, OAuthProvider

settings = get_settings()
logger = structlog.get_logger(__name__)


class OAuthService:
    """OAuth authentication service for social logins."""
    
    def __init__(self):
        # JWT configuration (same as AuthService)
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire = timedelta(hours=1)
        self.refresh_token_expire = timedelta(days=30)
        
        self.oauth = OAuth()
        
        # Configure Google OAuth
        if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
            self.oauth.register(
                name='google',
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
                client_kwargs={
                    'scope': 'openid email profile'
                }
            )
    
    def create_access_token(self, user: User) -> str:
        """Create JWT access token."""
        expire = datetime.utcnow() + self.access_token_expire
        to_encode = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "tenant_id": str(user.tenant_id) if user.tenant_id else "",
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token."""
        expire = datetime.utcnow() + self.refresh_token_expire
        to_encode = {
            "sub": str(user.id),
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": secrets.token_hex(16)  # Unique token ID
        }
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    async def generate_oauth_url(
        self,
        provider: str,
        client_request: Request,  # Add request object
        redirect_url: Optional[str] = None,
        db: AsyncSession = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """Generate OAuth authorization URL with state protection."""
        
        if provider not in ['google']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported OAuth provider: {provider}"
            )
        
        # Generate secure state token
        state_token = secrets.token_urlsafe(32)
        
        # Store state in database for CSRF protection
        if db:
            oauth_state = OAuthState(
                state_token=state_token,
                provider=provider,
                redirect_url=redirect_url or settings.OAUTH_REDIRECT_URL,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=datetime.utcnow() + timedelta(minutes=10)  # 10 minute expiry
            )
            db.add(oauth_state)
            await db.commit()
        
        # Generate OAuth URL
        if provider == 'google':
            client = self.oauth.google
            
            # Use await for authorize_redirect which is an async method
            redirect_uri = f"{settings.API_V1_PREFIX}/auth/oauth/callback/google"
            response = await client.authorize_redirect(
                request=client_request,  # Pass the request object
                redirect_uri=redirect_uri,
                state=state_token,
                access_type='offline',
                prompt='consent'
            )
            # The URL is in the response headers
            return response.headers['location']
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth provider not configured"
        )
    
    async def handle_oauth_callback(
        self,
        provider: str,
        code: str,
        state: str,
        db: AsyncSession,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle OAuth callback and create/link user account."""
        
        # Verify state token
        result = await db.execute(
            select(OAuthState).filter(
                OAuthState.state_token == state,
                OAuthState.provider == provider,
                OAuthState.is_used == False,
                OAuthState.expires_at > datetime.utcnow()
            )
        )
        oauth_state = result.scalar_one_or_none()
        
        if not oauth_state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth state"
            )
        
        # Mark state as used
        oauth_state.is_used = True
        oauth_state.used_at = datetime.utcnow()
        
        try:
            # Exchange code for tokens
            if provider == 'google':
                user_info = await self._handle_google_callback(code, db)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported provider: {provider}"
                )
            
            # Find or create user
            user = await self._find_or_create_user(user_info, provider, db)
            
            # Create authentication tokens
            access_token = self.create_access_token(user)
            refresh_token = self.create_refresh_token(user)
            
            # Log successful OAuth login
            logger.info(
                "OAuth login successful",
                provider=provider,
                user_id=str(user.id),
                email=user.email,
                ip_address=ip_address
            )
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "role": user.role.value,
                    "status": user.status.value,
                    "mfa_enabled": user.two_factor_enabled
                },
                "redirect_url": oauth_state.redirect_url
            }
            
        except Exception as e:
            logger.error("OAuth callback failed", provider=provider, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth authentication failed"
            )
        finally:
            await db.commit()
    
    async def _handle_google_callback(self, code: str, db: AsyncSession) -> Dict[str, Any]:
        """Handle Google OAuth callback."""
        
        # Exchange code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": f"{settings.API_V1_PREFIX}/auth/oauth/callback/google"
        }
        
        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=token_data)
            token_response.raise_for_status()
            tokens = token_response.json()
        
        # Get user info from Google
        user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        async with httpx.AsyncClient() as client:
            user_response = await client.get(user_info_url, headers=headers)
            user_response.raise_for_status()
            user_data = user_response.json()
        
        return {
            "provider": "google",
            "provider_user_id": user_data["id"],
            "email": user_data["email"],
            "name": user_data.get("name", ""),
            "avatar_url": user_data.get("picture"),
            "profile_data": user_data,
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "token_expires_at": datetime.utcnow() + timedelta(seconds=tokens.get("expires_in", 3600))
        }
    
    async def _find_or_create_user(
        self,
        user_info: Dict[str, Any],
        provider: str,
        db: AsyncSession
    ) -> User:
        """Find existing user or create new one from OAuth data."""
        
        provider_user_id = user_info["provider_user_id"]
        email = user_info["email"]
        
        # First, check if OAuth connection already exists
        result = await db.execute(
            select(UserOAuthConnection).filter(
                UserOAuthConnection.provider == provider,
                UserOAuthConnection.provider_user_id == provider_user_id
            )
        )
        oauth_connection = result.scalar_one_or_none()
        
        if oauth_connection:
            # Update existing connection
            oauth_connection.access_token = user_info["access_token"]
            oauth_connection.refresh_token = user_info.get("refresh_token")
            oauth_connection.token_expires_at = user_info.get("token_expires_at")
            oauth_connection.profile_data = user_info["profile_data"]
            oauth_connection.avatar_url = user_info.get("avatar_url")
            oauth_connection.last_used_at = datetime.utcnow()
            
            return oauth_connection.user
        
        # Check if user exists by email
        result = await db.execute(select(User).filter(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            # Create new user
            user = User(
                email=email,
                hashed_password="",  # OAuth users don't have passwords
                role=UserRole.TRADER,
                status=UserStatus.ACTIVE,  # OAuth users are automatically active
                is_active=True,
                is_verified=True  # Email verified by OAuth provider
            )
            db.add(user)
            await db.flush()  # Get user ID
            
            # Create user profile
            from app.models.user import UserProfile
            name_parts = user_info.get("name", "").split(" ", 1)
            profile = UserProfile(
                user_id=user.id,
                first_name=name_parts[0] if name_parts else "",
                last_name=name_parts[1] if len(name_parts) > 1 else "",
                avatar_url=user_info.get("avatar_url")
            )
            db.add(profile)
        
        # Create OAuth connection
        oauth_connection = UserOAuthConnection(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=email,
            access_token=user_info["access_token"],
            refresh_token=user_info.get("refresh_token"),
            token_expires_at=user_info.get("token_expires_at"),
            profile_data=user_info["profile_data"],
            avatar_url=user_info.get("avatar_url"),
            last_used_at=datetime.utcnow()
        )
        db.add(oauth_connection)
        
        return user
    
    async def link_oauth_account(
        self,
        user_id: uuid.UUID,
        provider: str,
        oauth_data: Dict[str, Any],
        db: AsyncSession
    ) -> UserOAuthConnection:
        """Link OAuth account to existing user."""
        
        # Check if connection already exists
        result = await db.execute(
            select(UserOAuthConnection).filter(
                UserOAuthConnection.user_id == user_id,
                UserOAuthConnection.provider == provider
            )
        )
        existing_connection = result.scalar_one_or_none()
        
        if existing_connection:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{provider.title()} account already linked"
            )
        
        # Create new connection
        oauth_connection = UserOAuthConnection(
            user_id=user_id,
            provider=provider,
            provider_user_id=oauth_data["provider_user_id"],
            provider_email=oauth_data["email"],
            access_token=oauth_data["access_token"],
            refresh_token=oauth_data.get("refresh_token"),
            token_expires_at=oauth_data.get("token_expires_at"),
            profile_data=oauth_data["profile_data"],
            avatar_url=oauth_data.get("avatar_url")
        )
        
        db.add(oauth_connection)
        await db.commit()
        
        return oauth_connection
    
    async def unlink_oauth_account(
        self,
        user_id: uuid.UUID,
        provider: str,
        db: AsyncSession
    ) -> bool:
        """Unlink OAuth account from user."""
        
        result = await db.execute(
            select(UserOAuthConnection).filter(
                UserOAuthConnection.user_id == user_id,
                UserOAuthConnection.provider == provider
            )
        )
        oauth_connection = result.scalar_one_or_none()
        
        if not oauth_connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{provider.title()} account not linked"
            )
        
        await db.delete(oauth_connection)
        await db.commit()
        
        return True
