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
from typing import Optional, Dict, Any
import sqlite3
import json

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import uvicorn
import jwt
import bcrypt

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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
)

# Security
security = HTTPBearer()

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
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """Get current authenticated user."""
    token = credentials.credentials
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
    return {"message": "CryptoUniverse API Running"}

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
