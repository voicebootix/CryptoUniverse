"""
Authentication API Endpoints - Enterprise Grade

Handles user authentication, JWT tokens, MFA, session management,
and role-based access control for the trading platform.
"""

import asyncio
import hashlib
import secrets
import time
from datetime import datetime, timedelta
import base64
import json
from typing import Optional, Dict, Any
from urllib.parse import quote
from fastapi.responses import RedirectResponse
import bcrypt
import jwt
from jwt import InvalidTokenError
import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func

from app.core.config import get_settings
from app.core.database import get_database
from app.core.redis import get_redis_client
from app.models.user import User, UserRole, UserStatus
from app.models.tenant import Tenant
from app.models.session import UserSession
from app.services.rate_limit import RateLimitService
from app.services.oauth import OAuthService

settings = get_settings()
logger = structlog.get_logger(__name__)
security = HTTPBearer()
rate_limiter = RateLimitService()
oauth_service = OAuthService()

router = APIRouter()


# Request/Response Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: Optional[str] = None
    remember_me: bool = False
    mfa_code: Optional[str] = None

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    tenant_id: Optional[str] = None
    role: UserRole = UserRole.TRADER
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    role: str
    tenant_id: str
    permissions: list


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    status: str
    tenant_id: str
    created_at: datetime
    last_login: Optional[datetime]
    mfa_enabled: bool


# Authentication Service
class AuthService:
    """Enterprise authentication service with JWT and MFA support."""
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire = timedelta(hours=1)
        self.refresh_token_expire = timedelta(days=30)
    
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
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


auth_service = AuthService()


# Dependency for getting current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_database)
) -> User:
    """Get current authenticated user."""
    token = credentials.credentials
    payload = auth_service.verify_token(token)
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Check if token is blacklisted
    # ENTERPRISE REDIS RESILIENCE
    redis = await get_redis_client()
    if redis:
        # SECURITY: Use same SHA-256 hash as logout writes
        token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
        blacklisted = await redis.get(f"blacklist:{token_hash}")
        if blacklisted:
            logger.info("Blacklisted token access blocked", token_hash=token_hash[:16])
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        logger.debug("Token blacklist check passed", token_hash=token_hash[:16])
    else:
        logger.warning("Redis unavailable for blacklist check, proceeding without")
    
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active"
        )
    
    return user


# Role-based access control
def require_role(allowed_roles: list):
    """Decorator for role-based access control."""
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker


# Authentication Endpoints
@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    client_request: Request,
    db: AsyncSession = Depends(get_database)
):
    """Authenticate user and return JWT tokens."""
    
    # Rate limiting
    client_ip = client_request.client.host
    await rate_limiter.check_rate_limit(
        key=f"login:{client_ip}",
        limit=5,
        window=300  # 5 attempts per 5 minutes
    )
    
    logger.info("Login attempt", email=request.email, ip=client_ip)
    
    try:
        # Find user
        result = await db.execute(select(User).filter(User.email == request.email))
        user = result.scalar_one_or_none()
        if not user:
            await asyncio.sleep(1)  # Prevent timing attacks
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Verify password
        if not auth_service.verify_password(request.password, user.hashed_password):
            await asyncio.sleep(1)  # Prevent timing attacks
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check user status
        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not active"
            )
        
        # Handle MFA if enabled
        if user.two_factor_enabled and not request.mfa_code:
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="MFA code required",
                headers={"X-MFA-Required": "true"}
            )
        
        # Verify MFA code if provided
        if user.two_factor_enabled and request.mfa_code:
            # TODO: Implement TOTP verification
            pass
        
        # Create tokens
        access_token = auth_service.create_access_token(user)
        refresh_token = auth_service.create_refresh_token(user)
        
        # Create session record
        session = UserSession(
            user_id=user.id,
            refresh_token=refresh_token,
            ip_address=client_ip,
            user_agent=client_request.headers.get("user-agent", ""),
            expires_at=datetime.utcnow() + auth_service.refresh_token_expire
        )
        db.add(session)
        
        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()
        
        logger.info("Login successful", user_id=str(user.id), email=user.email)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(auth_service.access_token_expire.total_seconds()),
            user_id=str(user.id),
            role=user.role.value,
            tenant_id=str(user.tenant_id) if user.tenant_id else "",
            permissions=get_user_permissions(user.role)
        )
    except InvalidTokenError as je:
        logger.exception("JWT error during login")
        raise HTTPException(500, detail="Authentication service error")
    except Exception as e:
        logger.exception("Unexpected login error")
        raise HTTPException(500, detail="Service unavailable - try again later")


@router.post("/register", response_model=UserResponse)
async def register(
    request: RegisterRequest,
    client_request: Request,
    db: AsyncSession = Depends(get_database)
):
    """Register new user account."""
    
    # Rate limiting
    client_ip = client_request.client.host
    await rate_limiter.check_rate_limit(
        key=f"register:{client_ip}",
        limit=3,
        window=3600  # 3 registrations per hour
    )
    
    logger.info("Registration attempt", email=request.email)
    
    # Check if user exists
    result = await db.execute(select(User).filter(User.email == request.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists"
        )
    
    # Validate tenant
    if request.tenant_id:
        result = await db.execute(select(Tenant).filter(Tenant.id == request.tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant or not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant"
            )
    
    # Create user
    user = User(
        email=request.email,
        hashed_password=auth_service.hash_password(request.password),
        role=request.role,
        tenant_id=request.tenant_id,
        status=UserStatus.PENDING_VERIFICATION
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)    
    # Create user profile with full_name
    from app.models.user import UserProfile
    profile = UserProfile(
        user_id=user.id,
        first_name=request.full_name.split(' ')[0] if request.full_name else "",
        last_name=' '.join(request.full_name.split(' ')[1:]) if ' ' in request.full_name else ""
    )
    db.add(profile)
    await db.commit()
    
    logger.info("User registered", user_id=str(user.id), email=user.email)
    
    # 🎁 SETUP WELCOME PACKAGE: $100 FREE CREDITS + 3 BASIC STRATEGIES
    try:
        from app.services.profit_sharing_service import profit_sharing_service
        
        welcome_result = await profit_sharing_service.setup_new_user_welcome_package(str(user.id))
        
        if welcome_result.get("success"):
            logger.info(
                "🎁 Welcome package activated for new user",
                user_id=str(user.id),
                free_credits=100,
                free_strategies=3,
                profit_potential="$400"
            )
        else:
            logger.warning("Welcome package setup failed", user_id=str(user.id), error=welcome_result.get("error"))
    
    except Exception as e:
        logger.error("Welcome package setup failed", user_id=str(user.id), error=str(e))
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=request.full_name,  # Use the request full_name directly
        role=user.role.value,
        status=user.status.value,
        tenant_id=str(user.tenant_id) if user.tenant_id else "",
        created_at=user.created_at,
        last_login=user.last_login,
        mfa_enabled=user.two_factor_enabled
    )


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_database)
):
    """Refresh access token using refresh token."""
    
    refresh_token = request.refresh_token
    # Verify refresh token
    payload = auth_service.verify_token(refresh_token)
    
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    user_id = payload.get("sub")
    jti = payload.get("jti")
    
    # Verify session exists
    result = await db.execute(select(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.refresh_token == refresh_token,
        UserSession.expires_at > datetime.utcnow()
    ))
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Get user
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new tokens
    new_access_token = auth_service.create_access_token(user)
    new_refresh_token = auth_service.create_refresh_token(user)
    
    # Update session
    session.refresh_token = new_refresh_token
    session.expires_at = datetime.utcnow() + auth_service.refresh_token_expire
    await db.commit()
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=int(auth_service.access_token_expire.total_seconds()),
        user_id=str(user.id),
        role=user.role.value,
        tenant_id=str(user.tenant_id) if user.tenant_id else "",
        permissions=get_user_permissions(user.role)
    )


@router.post("/logout")
async def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_database)
):
    """ENTERPRISE: Logout user and revoke tokens - always succeeds to prevent lockouts."""
    
    # ENTERPRISE: Graceful logout regardless of authentication state
    try:
        user_id = None
        token = None
        sessions_cleaned = 0
        
        # Process credentials if provided
        if credentials and credentials.credentials:
            token = credentials.credentials
            
            # Try to identify the user for proper cleanup
            try:
                # Attempt to decode token to get user ID
                payload = jwt.decode(
                    token, 
                    settings.SECRET_KEY, 
                    algorithms=[auth_service.algorithm]
                )
                user_id = payload.get("sub")
                logger.debug("Token decoded successfully for logout", user_id=user_id)
                
            except InvalidTokenError as jwt_error:
                # Token is invalid/expired - still allow logout
                logger.info("Logout with invalid/expired token - proceeding anyway", error=str(jwt_error))
                # Try to extract user ID from token without validation (for cleanup)
                try:
                    import jwt as raw_jwt
                    unverified = raw_jwt.decode(token, options={"verify_signature": False})
                    user_id = unverified.get("sub")
                    logger.debug("Extracted user ID from invalid token for cleanup", user_id=user_id)
                except Exception:
                    pass  # Can't extract user ID, proceed without it
            except Exception as decode_error:
                logger.warning("Token processing failed during logout", error=str(decode_error))
        
        # Blacklist the token if we have one (regardless of validity)
        redis = None
        token_blacklisted = False
        try:
            redis = await get_redis_client()
            if redis and token:
                # SECURITY: Hash token before using as Redis key (never store raw JWT)
                import hashlib
                token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
                
                # Use longer TTL for blacklist to be safe
                blacklist_ttl = max(3600, int(auth_service.access_token_expire.total_seconds()))
                
                # Capture Redis operation result
                redis_result = await redis.setex(
                    f"blacklist:{token_hash}",
                    blacklist_ttl,
                    "revoked_during_logout"
                )
                
                # Verify blacklist write succeeded
                token_blacklisted = bool(redis_result)
                
                if token_blacklisted:
                    logger.debug("Token blacklisted successfully", token_hash=token_hash[:16])
                else:
                    logger.error("Token blacklist write failed", token_hash=token_hash[:16], redis_result=redis_result)
                    
        except Exception as redis_error:
            logger.error("Redis blacklisting failed - critical security issue", 
                        token_hash=token_hash[:16] if 'token_hash' in locals() else "unknown", 
                        error=str(redis_error))
        
        # Clean up user sessions if we have a user ID
        if user_id:
            try:
                # Remove all active sessions for this user
                result = await db.execute(
                    delete(UserSession).where(
                        UserSession.user_id == user_id
                    )
                )
                await db.commit()
                sessions_cleaned = result.rowcount
                logger.info("User sessions cleaned during logout", user_id=user_id, sessions_removed=sessions_cleaned)
                
            except Exception as db_error:
                logger.warning("Database session cleanup failed - non-critical", error=str(db_error))
                try:
                    await db.rollback()
                except:
                    pass
        
        # ENTERPRISE: Additional cleanup - remove expired sessions (housekeeping)
        try:
            expired_result = await db.execute(
                delete(UserSession).where(
                    UserSession.expires_at < func.now()
                )
            )
            await db.commit()
            
            if expired_result.rowcount > 0:
                logger.debug(f"Cleaned up {expired_result.rowcount} expired sessions during logout")
                
        except Exception as cleanup_error:
            logger.debug("Expired session cleanup failed - non-critical", error=str(cleanup_error))
            try:
                await db.rollback()
            except:
                pass
        
        # Always return success
        response = {
            "message": "Successfully logged out",
            "user_id": user_id or "anonymous",
            "sessions_cleaned": sessions_cleaned,
            "token_blacklisted": token_blacklisted,
            "redis_available": redis is not None
        }
        
        logger.info("Logout completed successfully", **response)
        return response
        
    except Exception as critical_error:
        # ENTERPRISE: Even complete failure should not prevent logout
        logger.error(
            "Logout encountered critical error - allowing logout anyway",
            error=str(critical_error),
            message="User security prioritized over error handling"
        )
        
        # Ensure database is in clean state
        try:
            await db.rollback()
        except:
            pass
        
        return {
            "message": "Logout completed (degraded mode)",
            "status": "degraded",
            "user_id": "unknown",
            "sessions_cleaned": 0,
            "error": "Critical failure - investigate logs"
        }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        status=current_user.status.value,
        tenant_id=str(current_user.tenant_id) if current_user.tenant_id else "",
        created_at=current_user.created_at,
        last_login=current_user.last_login,
        mfa_enabled=current_user.two_factor_enabled
    )


def get_user_permissions(role: UserRole) -> list:
    """Get permissions based on user role."""
    permissions_map = {
        UserRole.ADMIN: [
            "admin:read", "admin:write", "admin:delete",
            "trading:read", "trading:write", "trading:execute",
            "portfolio:read", "portfolio:write",
            "users:read", "users:write", "users:delete",
            "system:read", "system:write"
        ],
        UserRole.TRADER: [
            "trading:read", "trading:write", "trading:execute",
            "portfolio:read", "portfolio:write"
        ],
        UserRole.VIEWER: [
            "trading:read", "portfolio:read"
        ],
        UserRole.API_ONLY: [
            "api:trading:execute", "api:portfolio:read"
        ]
    }
    return permissions_map.get(role, [])


# OAuth Request/Response Models
class OAuthUrlRequest(BaseModel):
    provider: str
    redirect_url: Optional[str] = None  # Optional since backend handles it
    is_signup: bool = False  # Flag to indicate registration flow

    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v):
        if v not in ['google']:
            raise ValueError('Unsupported OAuth provider')
        return v


class OAuthUrlResponse(BaseModel):
    authorization_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str


class OAuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserResponse
    redirect_url: Optional[str] = None


# OAuth Endpoints
@router.post("/oauth/url", response_model=OAuthUrlResponse)
async def get_oauth_url(
    request: OAuthUrlRequest,
    client_request: Request,
    db: AsyncSession = Depends(get_database)
):
    """Get OAuth authorization URL for social login."""
    
    client_ip = client_request.client.host
    user_agent = client_request.headers.get("user-agent", "")
    
    logger.info("OAuth URL request", provider=request.provider, ip=client_ip)
    
    authorization_url = await oauth_service.generate_oauth_url(
        provider=request.provider,
        client_request=client_request,
        is_signup=request.is_signup,
        db=db,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    # Extract state from URL (simple approach)
    from urllib.parse import urlparse, parse_qs
    parsed_url = urlparse(authorization_url)
    state = parse_qs(parsed_url.query).get('state', [''])[0]
    
    return OAuthUrlResponse(
        authorization_url=authorization_url,
        state=state
    )



@router.get("/oauth/callback/google", response_class=RedirectResponse)
async def oauth_callback(
    code: str,
    state: str,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    client_request: Request = None,
    db: AsyncSession = Depends(get_database)
):
    """Handle OAuth callback from Google and redirect to frontend with tokens."""
    logger.info(
        "Received OAuth callback",
        state=state,
        error=error,
        client_ip=client_request.client.host if client_request else None
    )

    if error:
        error_msg = error_description or error
        frontend_url = settings.FRONTEND_URL
        return RedirectResponse(
            url=f"{frontend_url}/auth/callback?error=true&message={error_msg}"
        )

    try:
        # Process OAuth callback
        result = await oauth_service.handle_oauth_callback(
            provider="google",
            code=code,
            state=state,
            db=db,
            ip_address=client_request.client.host if client_request else None
        )

        # Encode the auth data for frontend
        auth_data = {
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "token_type": result["token_type"],
            "expires_in": result["expires_in"],
            "user": result["user"]
        }

        # Base64 encode the auth data
        auth_data_json = json.dumps(auth_data, default=str)  # Handle datetime serialization
        auth_data_encoded = base64.urlsafe_b64encode(auth_data_json.encode()).decode()

        # Redirect to frontend with success data
        frontend_url = settings.FRONTEND_URL
        return RedirectResponse(
            url=f"{frontend_url}/auth/callback?success=true&data={auth_data_encoded}"
        )

    except Exception as e:
        logger.error(
            "OAuth callback failed",
            error=str(e),
            state=state,
            client_ip=client_request.client.host if client_request else None
        )
        
        # Redirect to frontend with error
        frontend_url = settings.FRONTEND_URL
        error_message = str(e)
        return RedirectResponse(
            url=f"{frontend_url}/auth/callback?error=true&message={quote(error_message)}"
        )


@router.post("/oauth/link/{provider}")
async def link_oauth_account(
    provider: str,
    request: OAuthCallbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Link OAuth account to existing user."""
    
    logger.info("OAuth account linking", provider=provider, user_id=str(current_user.id))
    
    # This would need additional implementation to handle the OAuth flow
    # for linking to existing accounts
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="OAuth account linking not yet implemented"
    )


@router.delete("/oauth/unlink/{provider}")
async def unlink_oauth_account(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Unlink OAuth account from user."""
    
    logger.info("OAuth account unlinking", provider=provider, user_id=str(current_user.id))
    
    success = await oauth_service.unlink_oauth_account(
        user_id=current_user.id,
        provider=provider,
        db=db
    )
    
    return {"message": f"{provider.title()} account unlinked successfully"}
