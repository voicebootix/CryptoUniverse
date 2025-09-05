"""
Password Reset API Endpoints
"""

from datetime import datetime, timedelta
import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_database
from app.core.config import get_settings
from app.models.user import User
from app.services.rate_limit import RateLimitService
import structlog

settings = get_settings()
logger = structlog.get_logger(__name__)
rate_limiter = RateLimitService()

router = APIRouter(prefix="/auth", tags=["Authentication"])

class ForgotPasswordRequest(BaseModel):
    """Request model for forgot password."""
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    """Request model for password reset."""
    token: str
    new_password: str

    class Config:
        json_schema_extra = {
            "example": {
                "token": "reset_token_here",
                "new_password": "NewSecurePassword123!"
            }
        }

@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    client_request: Request,
    db: AsyncSession = Depends(get_database)
):
    """
    Initiate password reset process.
    Sends a password reset link to the user's email.
    """
    try:
        # Rate limiting
        client_ip = client_request.client.host
        await rate_limiter.check_rate_limit(
            key=f"forgot_password:{client_ip}",
            limit=3,
            window=3600  # 3 requests per hour
        )

        # Find user
        result = await db.execute(
            select(User).filter(User.email == request.email)
        )
        user = result.scalar_one_or_none()

        if not user:
            # Return success even if user not found (security)
            return {"message": "If an account exists, reset instructions have been sent."}

        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        reset_expires = datetime.utcnow() + timedelta(hours=1)

        # Store reset token
        user.password_reset_token = reset_token
        user.password_reset_expires = reset_expires
        await db.commit()

        # Send reset email
        reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={reset_token}"
        # TODO: Implement email sending
        logger.info(
            "Password reset requested",
            user_id=str(user.id),
            email=user.email,
            reset_url=reset_url
        )

        return {
            "message": "If an account exists, reset instructions have been sent."
        }

    except Exception as e:
        logger.error("Password reset request failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password reset request"
        )

@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_database)
):
    """
    Reset password using the reset token.
    """
    try:
        # Find user with valid reset token
        result = await db.execute(
            select(User).filter(
                User.password_reset_token == request.token,
                User.password_reset_expires > datetime.utcnow()
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        # Update password
        from app.api.v1.endpoints.auth import auth_service
        user.hashed_password = auth_service.hash_password(request.new_password)
        
        # Clear reset token
        user.password_reset_token = None
        user.password_reset_expires = None
        
        await db.commit()

        logger.info("Password reset successful", user_id=str(user.id))
        
        return {"message": "Password has been reset successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Password reset failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )
