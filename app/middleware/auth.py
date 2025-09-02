"""
Authentication middleware for CryptoUniverse Enterprise.
Handles JWT validation, token refresh, and request authentication.
"""

import logging
from typing import Optional, Dict, Any, Tuple
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, JSONResponse

from app.core.security import (
    verify_access_token,
    verify_refresh_token,
    is_token_revoked,
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH
)
from app.core.redis import get_redis_client
from app.core.logging import logger

# Paths that don't require authentication
PUBLIC_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/register",
    "/api/v1/health",
    "/docs",
    "/openapi.json",
    "/redoc"
}

# Paths that require a valid token but not necessarily authentication
PROTECTED_PATHS = {
    "/api/v1/auth/logout"
}

# Token refresh threshold in seconds (5 minutes before expiration)
TOKEN_REFRESH_THRESHOLD = 300


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware that handles JWT validation and token refresh.
    
    This middleware:
    1. Validates JWT tokens for protected routes
    2. Handles token refresh when access token is about to expire
    3. Attaches user context to the request object
    4. Implements token revocation checking
    """
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Process incoming request with authentication.
        
        Args:
            request: The incoming request
            call_next: Next middleware or route handler
            
        Returns:
            Response: The HTTP response
        """
        # Skip authentication for public paths
        if request.url.path in PUBLIC_PATHS or any(request.url.path.startswith(p) for p in [
            "/static/", 
            "/health"
        ]):
            return await call_next(request)
            
        # Get authorization header
        auth_header = request.headers.get("Authorization")
        
        # For protected but not strictly authenticated endpoints
        if not auth_header and request.url.path in PROTECTED_PATHS:
            return await call_next(request)
            
        # Require authentication for all other endpoints
        if not auth_header:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing authorization header"}
            )
            
        # Extract token
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                raise ValueError("Invalid authorization scheme")
        except ValueError as e:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authorization header format"}
            )
            
        try:
            # Verify access token
            payload = verify_access_token(token)
            
            # Check if token is revoked
            if is_token_revoked(payload["jti"]):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Token has been revoked"}
                )
                
            # Check if token needs refresh (expiring soon)
            needs_refresh = False
            if "exp" in payload:
                from datetime import datetime, timezone
                now = datetime.now(tz=timezone.utc).timestamp()
                expires_at = payload["exp"]
                needs_refresh = (expires_at - now) < TOKEN_REFRESH_THRESHOLD
            
            # Attach user context to request
            request.state.user = {
                "id": payload["sub"],
                "role": payload.get("role"),
                "is_admin": payload.get("is_admin", False),
                "scopes": payload.get("scopes", []),
                "session_id": payload.get("sid")
            }
            
            # Process the request
            response = await call_next(request)
            
            # If token needs refresh, add new access token to response
            if needs_refresh and request.url.path not in PROTECTED_PATHS:
                try:
                    # Get refresh token from cookies
                    refresh_token = request.cookies.get("refresh_token")
                    if refresh_token:
                        refresh_payload = verify_refresh_token(refresh_token)
                        if refresh_payload["sub"] == payload["sub"]:
                            # Generate new access token
                            from app.core.security import create_access_token
                            from app.models.user import User
                            
                            user = User(id=payload["sub"], role=payload.get("role", "user"))
                            new_token, _ = create_access_token(
                                user=user,
                                session_id=payload.get("sid")
                            )
                            
                            # Add new token to response headers
                            response.headers["X-New-Access-Token"] = new_token
                except Exception as e:
                    logger.warning(f"Failed to refresh token: {str(e)}")
            
            return response
            
        except JWTError as e:
            logger.warning(f"JWT validation failed: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"}
            )
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Authentication service error"}
            )


def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Dependency to get current user from request state.
    
    This can be used in route handlers to get the current user:
    
    @app.get("/me")
    async def get_me(current_user = Depends(get_current_user)):
        return {"user_id": current_user["id"]}
    """
    if not hasattr(request.state, "user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return request.state.user


def require_role(required_roles: list):
    """
    Dependency to require specific user roles.
    
    Example usage:
    
    @app.get("/admin")
    async def admin_route(user = Depends(require_role(["admin"]))):
        return {"message": "Admin access granted"}
    """
    def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") not in required_roles and not current_user.get("is_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker
