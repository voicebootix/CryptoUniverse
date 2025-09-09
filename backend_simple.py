#!/usr/bin/env python3
"""
Simplified but Complete CryptoUniverse Backend with Authentication
This version includes all necessary endpoints without complex dependencies
"""

import os
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Set
import sqlite3
import json
import base64

from fastapi import FastAPI, HTTPException, Depends, status, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import uvicorn
import jwt
import bcrypt
import logging

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv() # Load environment variables from .env file

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "YOUR_GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/api/v1/auth/oauth/callback")

# Database file
DB_FILE = "cryptouniverse.db"

# FastAPI app
app = FastAPI(
    title="CryptoUniverse Enterprise API",
    description="AI-powered cryptocurrency trading platform",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://cryptouniverse-frontend.onrender.com",
        "http://localhost:3000",
        "http://localhost:8080",
        "*"  # Allow all origins for now
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-New-Access-Token"],  # Expose auth header for frontend
)

# Security
security = HTTPBearer(auto_error=False)  # Make bearer token optional

# OAuth state tracking for CSRF protection with TTL
oauth_states: Dict[str, float] = {}  # state -> expiry_timestamp

def cleanup_expired_states():
    """Remove expired OAuth states."""
    current_time = time.time()
    expired_states = [state for state, expiry in oauth_states.items() if expiry < current_time]
    for state in expired_states:
        oauth_states.pop(state, None)

# Models
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str = "User"
    role: str = "trader"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    role: str
    email: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    status: str
    created_at: datetime

class PortfolioResponse(BaseModel):
    total_value: float
    available_balance: float
    total_pnl: float
    daily_pnl_pct: float
    positions: list[Dict[str, Any]]

class TradingStatusResponse(BaseModel):
    overall_status: str
    system_health: Dict[str, Any]
    message: str
    performance_today: Dict[str, Any]

class MarketOverviewResponse(BaseModel):
    market_data: list[Dict[str, Any]]

class RecentTradesResponse(BaseModel):
    recent_trades: list[Dict[str, Any]]

class OAuthUrlResponse(BaseModel):
    authorization_url: str

class TokenData(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_id: str
    role: str
    email: str

# Database functions
def init_database():
    """Initialize SQLite database with users table."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT DEFAULT 'trader',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def create_admin_user():
    """Create default admin user if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check if admin exists
    cursor.execute("SELECT COUNT(*) FROM users WHERE email = ?", ("admin@cryptouniverse.com",))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return
    
    # Create admin user
    admin_id = secrets.token_hex(16)
    password = "AdminPass123!"
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    cursor.execute("""
        INSERT INTO users (id, email, password_hash, full_name, role, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (admin_id, "admin@cryptouniverse.com", password_hash, "System Administrator", "admin", "active"))
    
    conn.commit()
    conn.close()
    print(f"✅ Admin user created: admin@cryptouniverse.com / {password}")

def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email from database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return dict(user)
    return None

def create_user(email: str, password: str, full_name: str, role: str = "trader") -> Dict:
    """Create new user in database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    user_id = secrets.token_hex(16)
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    cursor.execute("""
        INSERT INTO users (id, email, password_hash, full_name, role, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, email, password_hash, full_name, role, "active"))
    
    conn.commit()
    conn.close()
    
    return {
        "id": user_id,
        "email": email,
        "full_name": full_name,
        "role": role,
        "status": "active",
        "created_at": datetime.utcnow()
    }

# JWT functions
def create_access_token(user: Dict) -> str:
    """Create JWT access token."""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"],
        "exp": expire
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Dict:
    """Verify JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

# Dependencies
async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict:
    """Get current authenticated user from bearer token or cookie."""
    
    token = None
    
    # Try bearer token first
    if credentials:
        token = credentials.credentials
    else:
        # Fallback to cookie-based authentication
        token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication provided",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    payload = verify_token(token)
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Get user from database
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return dict(user)

# Routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "CryptoUniverse API Running", "version": "2.0.1", "backend": "simplified"}

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}

@app.get("/api/v1/status")
async def api_status():
    """API status endpoint."""
    return {"status": "healthy", "service": "backend"}

@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    
    # Find user
    user = get_user_by_email(request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Verify password
    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Create token
    access_token = create_access_token(user)
    
    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user["id"],
        role=user["role"],
        email=user["email"]
    )

@app.post("/api/v1/auth/register", response_model=UserResponse)
async def register(request: RegisterRequest):
    """Register new user."""
    
    # Check if user exists
    existing_user = get_user_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists"
        )
    
    # Create user
    user = create_user(request.email, request.password, request.full_name, request.role)
    
    return UserResponse(**user)

@app.get("/api/v1/auth/me", response_model=UserResponse)
async def get_me(current_user: Dict = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        status=current_user["status"],
        created_at=datetime.fromisoformat(current_user["created_at"])
    )

@app.get("/api/v1/trading/portfolio", response_model=PortfolioResponse)
async def get_portfolio(current_user: Dict = Depends(get_current_user)):
    """Get user's trading portfolio."""
    # Updated to match frontend contract
    return PortfolioResponse(
        total_value=10000.00,
        available_balance=2500.00,
        total_pnl=1500.00,
        daily_pnl_pct=2.5,
        positions=[
            {
                "symbol": "BTC",
                "amount": 0.5,
                "avg_price": 30000.0,
                "market_value": 22500.0,
                "pnl": 2500.0
            },
            {
                "symbol": "ETH", 
                "amount": 3.0,
                "avg_price": 2000.0,
                "market_value": 6300.0,
                "pnl": 300.0
            }
        ]
    )

@app.get("/api/v1/trading/status", response_model=TradingStatusResponse)
async def get_trading_status(current_user: Dict = Depends(get_current_user)):
    """Get overall trading system status."""
    # Updated to match frontend contract
    return TradingStatusResponse(
        overall_status="Operational",
        system_health={
            "data_feeds": "Healthy",
            "execution_engine": "Healthy", 
            "risk_management": "Healthy",
        },
        message="All systems are functioning normally.",
        performance_today={
            "history": [
                {"timestamp": "2024-01-20T09:00:00Z", "pnl": 100.0},
                {"timestamp": "2024-01-20T12:00:00Z", "pnl": 150.0},
                {"timestamp": "2024-01-20T15:00:00Z", "pnl": 200.0}
            ]
        }
    )

@app.get("/api/v1/trading/market-overview", response_model=MarketOverviewResponse)
async def get_market_overview(current_user: Dict = Depends(get_current_user)):
    """Get market overview data."""
    # Updated to match frontend contract
    return MarketOverviewResponse(
        market_data=[
            {"symbol": "SOL", "change": 0.12, "price": 150.0, "trend": "up"},
            {"symbol": "ADA", "change": 0.08, "price": 0.75, "trend": "up"},
            {"symbol": "XRP", "change": -0.04, "price": 0.50, "trend": "down"},
            {"symbol": "DOGE", "change": -0.07, "price": 0.15, "trend": "down"},
            {"symbol": "BTC", "change": 0.02, "price": 45000.0, "trend": "up"},
            {"symbol": "ETH", "change": 0.03, "price": 3200.0, "trend": "up"}
        ]
    )

@app.get("/api/v1/trading/recent-trades", response_model=RecentTradesResponse)
async def get_recent_trades(current_user: Dict = Depends(get_current_user)):
    """Get recent trading activity."""
    # Updated to match frontend contract
    return RecentTradesResponse(
        recent_trades=[
            {"id": "trade1", "symbol": "BTC", "type": "buy", "amount": 0.1, "price": 31000.0, "timestamp": datetime.now().isoformat()},
            {"id": "trade2", "symbol": "ETH", "type": "sell", "amount": 0.5, "price": 2100.0, "timestamp": datetime.now().isoformat()},
        ]
    )

@app.get("/docs")
async def get_docs():
    """API documentation."""
    return {"message": "API Documentation", "endpoints": [
        "GET / - Root endpoint",
        "GET /health - Health check",
        "GET /api/v1/status - API status",
        "POST /api/v1/auth/login - User login",
        "POST /api/v1/auth/register - User registration",
        "GET /api/v1/auth/me - Current user info"
    ]}

@app.post("/api/v1/auth/logout")
async def logout(response: Response, current_user: Dict = Depends(get_current_user)):
    """Logout user and clear cookies."""
    # Clear the access token cookie
    response.delete_cookie(
        key="access_token",
        path="/",
        secure=True,
        httponly=True,
        samesite="none"
    )
    
    return {"message": "Logged out successfully"}

@app.post("/api/v1/auth/oauth/url", response_model=OAuthUrlResponse)
async def get_oauth_url():
    """Get the OAuth authorization URL with CSRF protection."""
    # Generate cryptographically secure state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Clean up expired states first
    cleanup_expired_states()
    
    # Add state with 10-minute expiry
    expiry_time = time.time() + (10 * 60)  # 10 minutes
    oauth_states[state] = expiry_time
    
    oauth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={GOOGLE_CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=email%20profile&state={state}"
    return OAuthUrlResponse(authorization_url=oauth_url)


@app.get("/api/v1/auth/oauth/callback")
async def oauth_callback(code: str, state: str, response: Response):
    """Handle OAuth callback from Google with CSRF protection."""
    # Clean up expired states first
    cleanup_expired_states()
    
    # Verify state parameter to prevent CSRF attacks
    if state not in oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter - possible CSRF attack"
        )
    
    # Check if state is expired
    if oauth_states[state] < time.time():
        oauth_states.pop(state, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State parameter expired"
        )
    
    # Remove used state
    oauth_states.pop(state, None)

    # Exchange authorization code for access token
    # This part would involve an HTTP POST request to Google's token endpoint.
    # For this example, we'll simulate a token exchange.
    # Replace with actual API call to Google for token exchange
    try:
        # Simulate Google token exchange and user info fetching
        # In a real app, use `httpx` or `requests` to call Google API
        # token_response = httpx.post("https://oauth2.googleapis.com/token", data={
        #     "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        #     "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        #     "code": code,
        #     "redirect_uri": "http://localhost:8000/api/v1/auth/oauth/callback",
        #     "grant_type": "authorization_code",
        # })
        # access_token = token_response.json()["access_token"]

        # user_info_response = httpx.get("https://www.googleapis.com/oauth2/v3/userinfo", headers={
        #     "Authorization": f"Bearer {access_token}"
        # })
        # google_user_info = user_info_response.json()

        # --- Placeholder for actual Google API calls ---
        # For demonstration, we'll create a dummy user based on the code
        dummy_email = f"user_{secrets.token_hex(4)}@example.com"
        dummy_full_name = f"OAuth User {secrets.token_hex(2)}"

        user = get_user_by_email(dummy_email)
        if not user:
            user = create_user(dummy_email, secrets.token_hex(16), dummy_full_name, "trader")
        
        access_token = create_access_token(user)

        # Prepare auth data for frontend
        auth_data = {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_id": user["id"],
            "role": user["role"],
            "email": user["email"],
            "user": {
                "id": user["id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "role": user["role"],
                "status": user["status"],
                "created_at": user["created_at"].isoformat() if hasattr(user["created_at"], 'isoformat') else str(user["created_at"]),
            },
        }

        # Set secure cookie instead of passing sensitive data in URL
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="none",  # Allow cross-site requests from frontend
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

        # Redirect to frontend with only success flag (no sensitive data in URL)
        redirect_url = f"http://localhost:3000/auth/oauth/callback?success=true"
        response.headers["Location"] = redirect_url
        response.status_code = status.HTTP_302_FOUND
        return response

    except Exception as e:
        # Log full exception server-side
        import uuid
        error_id = str(uuid.uuid4())
        logger.error(f"OAuth callback error [{error_id}]", exc_info=True)
        
        # Only send opaque error ID to frontend
        redirect_url = f"http://localhost:3000/auth/oauth/callback?error=true&error_id={error_id}"
        response.headers["Location"] = redirect_url
        response.status_code = status.HTTP_302_FOUND
        return response

# Startup
@app.on_event("startup")
async def startup_event():
    """Initialize application."""
    print("🚀 Starting CryptoUniverse Backend...")
    init_database()
    create_admin_user()
    print("✅ Backend ready!")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
