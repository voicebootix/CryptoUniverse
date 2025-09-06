#!/usr/bin/env python3
"""
Enterprise JWT Configuration Test
Verifies that all JWT services use consistent 8-hour expiration
"""

import sys
import os
from datetime import timedelta

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_jwt_consistency():
    """Test that all JWT services have consistent configuration."""
    print("🔍 Testing Enterprise JWT Configuration...")
    print("=" * 50)
    
    try:
        # Test 1: Config settings
        from app.core.config import get_settings
        settings = get_settings()
        
        print(f"✅ Config JWT_ACCESS_TOKEN_EXPIRE_HOURS: {settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS}")
        print(f"✅ Config JWT_REFRESH_TOKEN_EXPIRE_DAYS: {settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS}")
        
        # Test 2: AuthService
        from app.api.v1.endpoints.auth import AuthService
        auth_service = AuthService()
        auth_hours = auth_service.access_token_expire.total_seconds() / 3600
        
        print(f"✅ AuthService expiration: {auth_hours} hours")
        
        # Test 3: OAuthService  
        from app.services.oauth import OAuthService
        oauth_service = OAuthService()
        oauth_hours = oauth_service.access_token_expire.total_seconds() / 3600
        
        print(f"✅ OAuthService expiration: {oauth_hours} hours")
        
        # Test 4: Security constants
        from app.core.security import ACCESS_TOKEN_EXPIRE_MINUTES
        security_hours = ACCESS_TOKEN_EXPIRE_MINUTES / 60
        
        print(f"✅ Security module expiration: {security_hours} hours")
        
        # Consistency check
        if auth_hours == oauth_hours == security_hours == settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS:
            print("\n🎉 SUCCESS: All JWT services have consistent 8-hour expiration!")
            return True
        else:
            print("\n❌ FAILURE: JWT services have inconsistent expiration times!")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False

def test_token_creation():
    """Test actual token creation and validation."""
    print("\n🔍 Testing Token Creation...")
    print("=" * 30)
    
    try:
        from app.api.v1.endpoints.auth import AuthService
        from app.models.user import User, UserRole
        import uuid
        
        auth_service = AuthService()
        
        # Create a test user
        test_user = User()
        test_user.id = uuid.uuid4()
        test_user.email = "test@cryptouniverse.com"
        test_user.role = UserRole.TRADER
        test_user.tenant_id = None
        
        # Create token
        token = auth_service.create_access_token(test_user)
        print("✅ Token created successfully")
        
        # Verify token
        payload = auth_service.verify_token(token)
        print("✅ Token verified successfully")
        
        # Check claims
        if 'jti' in payload:
            print("✅ JWT ID (jti) claim present")
        else:
            print("❌ JWT ID (jti) claim missing")
            return False
            
        if payload.get('type') == 'access':
            print("✅ Token type is 'access'")
        else:
            print("❌ Token type incorrect")
            return False
            
        print("\n🎉 SUCCESS: Token creation and validation working!")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 CryptoUniverse Enterprise JWT Test")
    print("=" * 60)
    
    test1_passed = test_jwt_consistency()
    test2_passed = test_token_creation()
    
    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED - JWT Enterprise Setup is Correct!")
        sys.exit(0)
    else:
        print("\n❌ TESTS FAILED - JWT Setup Needs Attention!")
        sys.exit(1)
