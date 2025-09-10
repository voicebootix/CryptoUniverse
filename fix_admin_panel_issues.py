#!/usr/bin/env python3
"""
Comprehensive fix for admin panel database and performance issues.

Issues addressed:
1. Database connection timeout errors (28+ second login)
2. Admin API calls failing with empty responses
3. JWT token persistence issues
4. Database query optimization for admin panel
5. Connection pooling improvements for Render deployment
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add app to path
sys.path.append(str(Path(__file__).parent))

import structlog

logger = structlog.get_logger(__name__)


async def fix_database_connection_config():
    """Fix database connection configuration for better performance."""
    
    print("🔧 Fixing database connection configuration...")
    
    database_py_path = Path("app/core/database.py")
    
    # Read current configuration
    with open(database_py_path, 'r') as f:
        content = f.read()
    
    # Enhanced database configuration for Render production
    new_config = '''# ENTERPRISE SQLAlchemy async engine optimized for Render production
# Increased pool size and timeouts for admin panel performance
engine = create_async_engine(
    get_async_database_url(),
    poolclass=QueuePool,  # ENTERPRISE: Use proper connection pooling
    pool_size=10,         # PRODUCTION: Increased for admin panel (was 3)
    max_overflow=20,      # PRODUCTION: Increased overflow for peak load (was 2)
    pool_pre_ping=True,   # ENTERPRISE: Health check connections
    pool_recycle=3600,    # PRODUCTION: Increased recycle time (was 1800)
    pool_timeout=60,      # PRODUCTION: Increased timeout for admin queries (was 30)
    echo=getattr(settings, 'DATABASE_ECHO', False),
    future=True,
    # ENTERPRISE: Production performance settings
    execution_options={
        "isolation_level": "READ_COMMITTED",
        "compiled_cache": {},  # Enable query compilation cache
    },
    # PRODUCTION: Optimized settings for asyncpg driver with admin panel fixes
    connect_args={
        "command_timeout": 60,  # Increased command timeout for admin queries (was 30)
        "timeout": 120,         # Increased connection timeout for slow admin operations (was 60)
        "ssl": "require" if "supabase" in get_async_database_url().lower() else None,
        # Server settings for asyncpg with admin optimizations
        "server_settings": {
            "application_name": "cryptouniverse_production",
            "jit": "off",
            "work_mem": "16MB",           # Increased for admin queries
            "effective_cache_size": "1GB", # Better query planning
            "max_connections": "100"       # Ensure enough connections
        }
    } if "postgresql" in get_async_database_url() else {}
)'''
    
    # Replace the engine configuration
    import re
    pattern = r'engine = create_async_engine\(.*?\n\)'
    content = re.sub(pattern, new_config, content, flags=re.DOTALL)
    
    # Write back
    with open(database_py_path, 'w') as f:
        f.write(content)
    
    print("✅ Database connection configuration updated")


async def fix_admin_users_list_query():
    """Fix the admin users list query for better performance."""
    
    print("🔧 Optimizing admin users list query...")
    
    admin_py_path = Path("app/api/v1/endpoints/admin.py")
    
    # Read current file
    with open(admin_py_path, 'r') as f:
        content = f.read()
    
    # Add optimized query at the top of list_users function
    optimized_query = '''@router.get("/users", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    role_filter: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_role(["ADMIN", UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database)
):
    """List and filter users with optimized queries."""
    
    await rate_limiter.check_rate_limit(
        key="admin:list_users",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Build optimized base query with eager loading
        stmt = select(User).options()
        
        # SECURITY: Apply tenant isolation
        if current_user.tenant_id is not None:
            stmt = stmt.where(User.tenant_id == current_user.tenant_id)
        
        # Apply filters
        if status_filter:
            try:
                parsed_status = UserStatus(status_filter)
                stmt = stmt.where(User.status == parsed_status)
            except ValueError:
                logger.warning(f"Invalid status filter: {status_filter}")
        
        if role_filter:
            try:
                parsed_role = UserRole(role_filter)
                stmt = stmt.where(User.role == parsed_role)
            except ValueError:
                logger.warning(f"Invalid role filter: {role_filter}")
        
        if search:
            stmt = stmt.where(User.email.ilike(f"%{search}%"))
        
        # Get total count efficiently
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar_one()
        
        # Order and paginate
        stmt = stmt.order_by(User.created_at.desc(), User.id).offset(skip).limit(limit)
        
        # Execute with timeout
        result = await asyncio.wait_for(db.execute(stmt), timeout=30.0)
        users = result.scalars().all()
        
        # Batch fetch related data efficiently
        user_ids = [user.id for user in users]
        credit_map = {}
        trade_count_map = {}
        
        if user_ids:
            # Get credits in batch
            credit_results = await db.execute(
                select(CreditAccount.user_id, CreditAccount.available_credits)
                .where(CreditAccount.user_id.in_(user_ids))
            )
            credit_map = {row.user_id: row.available_credits for row in credit_results}
            
            # Get trade counts in batch
            trade_results = await db.execute(
                select(Trade.user_id, func.count().label("count"))
                .where(Trade.user_id.in_(user_ids))
                .group_by(Trade.user_id)
            )
            trade_count_map = {row.user_id: row.count for row in trade_results}
        
        # Count active/trading users efficiently
        if current_user.tenant_id is not None:
            active_count = await db.scalar(
                select(func.count()).select_from(User).where(
                    User.status == UserStatus.ACTIVE,
                    User.tenant_id == current_user.tenant_id
                )
            ) or 0
            
            trading_count = await db.scalar(
                select(func.count()).select_from(User).where(
                    User.status == UserStatus.ACTIVE,
                    User.role.in_([UserRole.TRADER, UserRole.ADMIN]),
                    User.tenant_id == current_user.tenant_id
                )
            ) or 0
        else:
            active_count = await db.scalar(
                select(func.count()).select_from(User).where(User.status == UserStatus.ACTIVE)
            ) or 0
            
            trading_count = await db.scalar(
                select(func.count()).select_from(User).where(
                    User.status == UserStatus.ACTIVE,
                    User.role.in_([UserRole.TRADER, UserRole.ADMIN])
                )
            ) or 0
        
        # Format response
        user_list = []
        for user in users:
            user_data = {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.email,  # Fallback to email
                "role": user.role.value,
                "status": user.status.value,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                "credits": credit_map.get(user.id, 0),
                "total_trades": trade_count_map.get(user.id, 0)
            }
            user_list.append(user_data)
        
        return UserListResponse(
            users=user_list,
            total_count=total_count,
            active_count=active_count,
            trading_count=trading_count
        )
        
    except asyncio.TimeoutError:
        logger.error("Admin users list query timeout")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Query timeout - try with filters to reduce results"
        )
    except Exception as e:
        logger.exception("User listing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        ) from e'''
    
    # Replace the existing function
    import re
    pattern = r'@router\.get\("/users", response_model=UserListResponse\).*?(?=@router\.|$)'
    content = re.sub(pattern, optimized_query, content, flags=re.DOTALL)
    
    # Write back
    with open(admin_py_path, 'w') as f:
        f.write(content)
    
    print("✅ Admin users list query optimized")


async def create_frontend_jwt_fix():
    """Create frontend fix for JWT token persistence."""
    
    print("🔧 Creating frontend JWT token persistence fix...")
    
    # Create a new auth store fix
    auth_store_fix = '''// Enhanced auth store with better token persistence
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface AuthState {
  user: any;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: any) => Promise<void>;
  logout: () => void;
  refreshAuth: () => Promise<boolean>;
  setToken: (token: string, refreshToken?: string) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,

      setToken: (token: string, refreshToken?: string) => {
        set({
          token,
          refreshToken: refreshToken || get().refreshToken,
          isAuthenticated: true
        });
        
        // Also set in localStorage as backup
        localStorage.setItem('auth_token', token);
        if (refreshToken) {
          localStorage.setItem('refresh_token', refreshToken);
        }
      },

      login: async (credentials: any) => {
        set({ isLoading: true });
        
        try {
          const response = await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include', // Important for cookies
            body: JSON.stringify(credentials),
          });

          if (!response.ok) {
            throw new Error('Login failed');
          }

          const data = await response.json();
          
          set({
            user: data.user,
            token: data.access_token,
            refreshToken: data.refresh_token,
            isAuthenticated: true,
            isLoading: false
          });

          // Backup storage
          localStorage.setItem('auth_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);
          localStorage.setItem('user_data', JSON.stringify(data.user));
          
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      logout: () => {
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
          isLoading: false
        });
        
        // Clear all storage
        localStorage.removeItem('auth_token');
        localStorage.removeItem('refresh_token'); 
        localStorage.removeItem('user_data');
        sessionStorage.clear();
      },

      refreshAuth: async () => {
        const refreshToken = get().refreshToken || localStorage.getItem('refresh_token');
        
        if (!refreshToken) {
          return false;
        }

        try {
          const response = await fetch('/api/v1/auth/refresh', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${refreshToken}`,
              'Content-Type': 'application/json'
            },
            credentials: 'include'
          });

          if (!response.ok) {
            throw new Error('Token refresh failed');
          }

          const data = await response.json();
          get().setToken(data.access_token, data.refresh_token);
          
          return true;
        } catch (error) {
          console.error('Token refresh failed:', error);
          get().logout();
          return false;
        }
      }
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
);

// Initialize auth from storage on app start
if (typeof window !== 'undefined') {
  const token = localStorage.getItem('auth_token');
  const refreshToken = localStorage.getItem('refresh_token');
  const userData = localStorage.getItem('user_data');
  
  if (token && userData) {
    try {
      const user = JSON.parse(userData);
      useAuthStore.setState({
        user,
        token,
        refreshToken,
        isAuthenticated: true
      });
    } catch (error) {
      console.error('Failed to restore auth state:', error);
      useAuthStore.getState().logout();
    }
  }
}'''
    
    # Write the auth store fix
    frontend_path = Path("frontend/src/store/authStore.ts")
    frontend_path.parent.mkdir(exist_ok=True)
    
    with open(frontend_path, 'w') as f:
        f.write(auth_store_fix)
    
    print("✅ Frontend JWT token persistence fix created")


async def create_admin_panel_api_fix():
    """Create optimized admin panel API calls."""
    
    print("🔧 Creating optimized admin panel API fix...")
    
    admin_api_fix = '''// Optimized admin panel API with retry logic and better error handling
import { useAuthStore } from '../store/authStore';

class AdminAPI {
  private baseURL = '/api/v1/admin';
  private retryAttempts = 3;
  private retryDelay = 1000;

  private async fetchWithAuth(url: string, options: RequestInit = {}, attempt = 1): Promise<Response> {
    const { token, refreshAuth } = useAuthStore.getState();
    
    if (!token) {
      throw new Error('No authentication token');
    }

    const response = await fetch(`${this.baseURL}${url}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
      credentials: 'include',
      // Add timeout
      signal: AbortSignal.timeout(30000) // 30 second timeout
    });

    // Handle token expiration
    if (response.status === 401 && attempt <= this.retryAttempts) {
      const refreshed = await refreshAuth();
      if (refreshed) {
        return this.fetchWithAuth(url, options, attempt + 1);
      }
    }

    return response;
  }

  async getUsers(params: {
    skip?: number;
    limit?: number;
    status_filter?: string;
    role_filter?: string;
    search?: string;
  } = {}): Promise<any> {
    try {
      const queryParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          queryParams.append(key, value.toString());
        }
      });

      const url = `/users?${queryParams.toString()}`;
      const response = await this.fetchWithAuth(url);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: Failed to fetch users`);
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to fetch users:', error);
      throw error;
    }
  }

  async getSystemStatus(): Promise<any> {
    try {
      const response = await this.fetchWithAuth('/system/status');
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: Failed to fetch system status`);
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to fetch system status:', error);
      // Return default values if API fails
      return {
        system_health: 'unknown',
        active_users: 0,
        total_trades_today: 0,
        total_volume_24h: 0,
        autonomous_sessions: 0,
        error_rate: 0,
        response_time_avg: 0
      };
    }
  }

  async verifyUser(userId: string): Promise<any> {
    try {
      const response = await this.fetchWithAuth(`/users/verify/${userId}`, {
        method: 'POST'
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to verify user');
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to verify user:', error);
      throw error;
    }
  }

  async getPendingUsers(includeUnverified = false): Promise<any> {
    try {
      const url = `/users/pending-verification?include_unverified=${includeUnverified}`;
      const response = await this.fetchWithAuth(url);

      if (!response.ok) {
        throw new Error('Failed to fetch pending users');
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to fetch pending users:', error);
      throw error;
    }
  }

  async getMetrics(): Promise<any> {
    try {
      const response = await this.fetchWithAuth('/metrics');
      
      if (!response.ok) {
        throw new Error('Failed to fetch metrics');
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
      return {
        active_users: 0,
        total_trades_today: 0,
        total_volume_24h: 0,
        system_health: 'unknown',
        autonomous_sessions: 0,
        error_rate: 0,
        response_time_avg: 0,
        uptime_percentage: 0
      };
    }
  }
}

export const adminAPI = new AdminAPI();'''
    
    # Write the admin API fix
    frontend_api_path = Path("frontend/src/services/adminAPI.ts")
    frontend_api_path.parent.mkdir(exist_ok=True)
    
    with open(frontend_api_path, 'w') as f:
        f.write(admin_api_fix)
    
    print("✅ Optimized admin panel API created")


async def create_database_health_check():
    """Create database health check script."""
    
    print("🔧 Creating database health check...")
    
    health_check = '''#!/usr/bin/env python3
"""
Database health check and connection test for admin panel issues.
"""

import asyncio
import time
from app.core.database import AsyncSessionLocal, engine
from app.models.user import User, UserStatus
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError

async def test_database_connection():
    """Test database connection and basic queries."""
    
    print("🔍 Testing database connection...")
    
    try:
        start_time = time.time()
        
        # Test basic connection
        async with AsyncSessionLocal() as session:
            # Test simple query
            result = await session.execute(select(func.count()).select_from(User))
            user_count = result.scalar_one()
            
            connection_time = time.time() - start_time
            print(f"✅ Database connected in {connection_time:.2f}s")
            print(f"📊 Total users in database: {user_count}")
            
            # Test admin query performance
            start_time = time.time()
            result = await session.execute(
                select(User.id, User.email, User.status)
                .where(User.status == UserStatus.ACTIVE)
                .limit(10)
            )
            users = result.all()
            query_time = time.time() - start_time
            
            print(f"🚀 Admin query completed in {query_time:.2f}s")
            print(f"👥 Active users found: {len(users)}")
            
            if query_time > 5.0:
                print("⚠️  WARNING: Query is slow (>5s)")
            
            return True
            
    except SQLAlchemyError as e:
        print(f"❌ Database connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_database_connection())'''
    
    with open("test_database_health.py", 'w') as f:
        f.write(health_check)
    
    print("✅ Database health check script created")


async def main():
    """Run all fixes for admin panel issues."""
    
    print("🚀 Starting comprehensive admin panel fixes...")
    print("="*60)
    
    # Run all fixes
    await fix_database_connection_config()
    await fix_admin_users_list_query() 
    await create_frontend_jwt_fix()
    await create_admin_panel_api_fix()
    await create_database_health_check()
    
    print("="*60)
    print("✅ All admin panel fixes completed!")
    print()
    print("📋 Summary of changes:")
    print("1. ⚡ Increased database connection pool size and timeouts")
    print("2. 🔧 Optimized admin users list query with batch fetching")
    print("3. 🔐 Enhanced JWT token persistence in frontend")
    print("4. 📡 Created robust admin API with retry logic")
    print("5. 🏥 Added database health check script")
    print()
    print("🔄 Next steps:")
    print("1. Commit and push these changes")
    print("2. Redeploy on Render")
    print("3. Run: python test_database_health.py")
    print("4. Test admin panel login and user list")


if __name__ == "__main__":
    asyncio.run(main())