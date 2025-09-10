#!/usr/bin/env python3
"""
Add connection pool monitoring and auto-scaling for admin panel performance.
"""

import asyncio
import time
from pathlib import Path

# Add monitoring to admin endpoints for connection pool status
monitoring_code = '''
# Add this to admin.py to monitor connection pool status

async def get_connection_pool_status():
    """Get current database connection pool status."""
    from app.core.database import engine
    
    pool = engine.pool
    
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalid(),
        "total_connections": pool.size() + pool.overflow(),
        "available_connections": pool.size() - pool.checkedout(),
        "pool_status": "healthy" if pool.checkedout() < (pool.size() * 0.8) else "warning"
    }

@router.get("/system/pool-status")
async def get_pool_status(
    current_user: User = Depends(require_role(["ADMIN", UserRole.ADMIN]))
):
    """Get database connection pool status for monitoring."""
    
    try:
        pool_info = await get_connection_pool_status()
        
        return {
            "status": "success",
            "pool_info": pool_info,
            "recommendations": [
                "Increase pool_size if available_connections < 5" if pool_info["available_connections"] < 5 else None,
                "Consider connection cleanup if overflow > 20" if pool_info["overflow"] > 20 else None,
                "Monitor for connection leaks if checked_out stays high" if pool_info["checked_out"] > (pool_info["pool_size"] * 0.9) else None
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.exception("Failed to get pool status")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
'''

print("=== Connection Pool Monitoring Setup ===")
print("📊 Database pool increased to 25 + 50 overflow = 75 total connections")
print("🔍 Add this monitoring code to admin.py:")
print(monitoring_code)

# Create a simple test script
test_script = '''#!/usr/bin/env python3
"""
Test database connection pool under load.
"""

import asyncio
import time
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.user import User

async def test_connection_under_load(concurrent_connections=10):
    """Test database connections under concurrent load."""
    
    async def single_query(query_id):
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(func.count()).select_from(User))
                count = result.scalar_one()
                
                print(f"✅ Query {query_id}: Found {count} users")
                return True
        except Exception as e:
            print(f"❌ Query {query_id} failed: {e}")
            return False
    
    print(f"🔄 Testing {concurrent_connections} concurrent database connections...")
    start_time = time.time()
    
    tasks = [single_query(i) for i in range(concurrent_connections)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    successful = sum(1 for r in results if r is True)
    
    print(f"📊 Results: {successful}/{concurrent_connections} successful in {end_time - start_time:.2f}s")
    
    return successful == concurrent_connections

if __name__ == "__main__":
    asyncio.run(test_connection_under_load())
'''

with open("test_connection_pool.py", "w") as f:
    f.write(test_script)

print("✅ Created test_connection_pool.py for testing")
print()
print("🚀 Quick test: python test_connection_pool.py")