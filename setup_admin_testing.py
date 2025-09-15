#!/usr/bin/env python3
"""
Setup Admin Testing Environment

Sets up environment variables and validates admin testing capabilities.
"""

import os
import sys
from pathlib import Path

def setup_testing_environment():
    """Setup testing environment with proper validation."""
    
    print("🔧 ADMIN TESTING ENVIRONMENT SETUP")
    print("=" * 60)
    
    # Check if .env file exists
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        print("📄 Creating .env file from .env.example...")
        
        # Copy example to .env
        with open(env_example, 'r') as f:
            content = f.read()
        
        with open(env_file, 'w') as f:
            f.write(content)
        
        print("✅ Created .env file")
        print("⚠️  Please edit .env file with your actual values")
        print("   Then run this script again")
        return False
    
    # Load environment variables
    if env_file.exists():
        print("📄 Loading .env file...")
        try:
            from dotenv import load_dotenv
            load_dotenv()
            print("✅ Environment variables loaded")
        except ImportError:
            print("⚠️  python-dotenv not available, using system environment")
    
    # Validate required variables
    required_vars = {
        "BASE_URL": "API base URL for testing",
        "ADMIN_EMAIL": "Admin user email",
        "ADMIN_PASSWORD": "Admin user password"
    }
    
    missing_vars = []
    
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if not value or not value.strip():
            missing_vars.append((var_name, description))
        else:
            print(f"✅ {var_name}: Configured")
    
    if missing_vars:
        print(f"\n❌ Missing required environment variables:")
        for var_name, description in missing_vars:
            print(f"   {var_name}: {description}")
        
        print(f"\n💡 Set these variables in your .env file:")
        for var_name, _ in missing_vars:
            print(f"   {var_name}=your_value_here")
        
        return False
    
    # Validate BASE_URL format
    base_url = os.getenv("BASE_URL", "")
    if not base_url.startswith(("http://", "https://")):
        print(f"❌ BASE_URL must start with http:// or https://")
        return False
    
    print(f"\n✅ All environment variables configured correctly")
    return True

def create_testing_scripts():
    """Create testing scripts with environment variable support."""
    
    print(f"\n📄 Creating testing scripts...")
    
    # Create secure testing script
    secure_test_script = '''#!/usr/bin/env python3
"""
Secure Admin Strategy Testing

Uses environment variables for configuration.
"""

import os
import sys
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Set environment variables for testing
os.environ["BASE_URL"] = os.getenv("BASE_URL", "https://cryptouniverse.onrender.com/api/v1")
os.environ["ADMIN_EMAIL"] = os.getenv("ADMIN_EMAIL", "")
os.environ["ADMIN_PASSWORD"] = os.getenv("ADMIN_PASSWORD", "")

# Import and run the testing
try:
    from admin_testing_solution import test_all_strategies_directly
    test_all_strategies_directly()
except Exception as e:
    print(f"❌ Testing failed: {e}")
    sys.exit(1)
'''
    
    with open('secure_admin_test.py', 'w') as f:
        f.write(secure_test_script)
    
    print("✅ Created secure_admin_test.py")

def main():
    print("🎯 ADMIN TESTING SETUP")
    print("=" * 80)
    
    # Setup environment
    env_ready = setup_testing_environment()
    
    # Create scripts
    create_testing_scripts()
    
    if env_ready:
        print(f"\n🎉 ADMIN TESTING READY!")
        print("=" * 50)
        print("✅ Environment variables configured")
        print("✅ Testing scripts created")
        print("✅ Ready for comprehensive strategy testing")
        
        print(f"\n🚀 NEXT STEPS:")
        print("1. Run: python3 secure_admin_test.py")
        print("2. Test individual strategies via admin endpoints")
        print("3. Verify all 25 strategies after production restart")
    else:
        print(f"\n⚠️ SETUP INCOMPLETE")
        print("Please configure environment variables and run again")

if __name__ == "__main__":
    main()