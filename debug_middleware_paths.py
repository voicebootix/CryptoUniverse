#!/usr/bin/env python3
"""
Debug middleware path matching to understand why auth endpoints are blocked
"""

def test_path_matching():
    """Test how the middleware path matching works."""
    
    # Current PUBLIC_PATHS from middleware
    PUBLIC_PATHS = {
        "/api/v1/auth/login",
        "/api/v1/auth/refresh", 
        "/api/v1/auth/register",
        "/api/v1/health",
        "/api/v1/status",
        "/health",
        "/",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/metrics"
    }
    
    # Test paths that TestSprite is trying to access
    test_paths = [
        "/health",                    # Works
        "/api/v1/status",            # Should work
        "/auth/login",               # TestSprite is calling this
        "/auth/register",            # TestSprite is calling this
        "/auth/refresh",             # TestSprite is calling this
        "/api/v1/auth/login",        # Full path in PUBLIC_PATHS
        "/api/v1/auth/register",     # Full path in PUBLIC_PATHS
        "/api/v1/auth/refresh",      # Full path in PUBLIC_PATHS
    ]
    
    print("🔍 DEBUGGING MIDDLEWARE PATH MATCHING")
    print("=" * 60)
    
    print(f"\n📋 PUBLIC_PATHS configuration:")
    for path in sorted(PUBLIC_PATHS):
        print(f"   ✅ {path}")
    
    print(f"\n🧪 Testing path matching:")
    for test_path in test_paths:
        if test_path in PUBLIC_PATHS:
            print(f"   ✅ {test_path} - MATCHES (should be public)")
        else:
            print(f"   ❌ {test_path} - NO MATCH (will require auth)")
            
            # Check if there's a pattern match
            patterns = ["/static/", "/health", "/api/v1/trading/ws", "/vite.svg", "/login"]
            pattern_match = any(test_path.startswith(p) for p in patterns)
            
            if pattern_match:
                print(f"      ✅ But matches pattern - should be public")
            else:
                print(f"      ❌ No pattern match - WILL BE BLOCKED")
    
    print(f"\n💡 ISSUE IDENTIFIED:")
    print("TestSprite is calling '/auth/login' but middleware expects '/api/v1/auth/login'")
    print("This is a path prefix mismatch issue!")
    
    return test_paths

if __name__ == "__main__":
    test_path_matching()
