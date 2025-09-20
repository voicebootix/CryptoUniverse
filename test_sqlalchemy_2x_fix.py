#!/usr/bin/env python3
"""
Enterprise SQLAlchemy 2.x Fix Validation

This test validates the SQLAlchemy 2.x compatibility fix by testing:
1. Database architecture imports
2. Model loading and compatibility
3. Metadata schema property access
4. Declarative base functionality
5. Enterprise patterns implementation

Author: CTO Assistant
Date: September 20, 2025
"""

import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, '/workspace')

def test_database_imports():
    """Test that the new database architecture imports correctly."""
    print("🗄️ Testing Database Architecture Imports...")
    
    try:
        from app.core.database import Base, metadata, engine, AsyncSessionLocal
        print("✅ Database core imports successful")
        return True
    except Exception as e:
        print(f"❌ Database import failed: {e}")
        return False

def test_base_class_structure():
    """Test the new Base class structure."""
    print("\n🏗️ Testing SQLAlchemy 2.x Base Class Structure...")
    
    try:
        from app.core.database import Base, EnterpriseBase
        
        # Check if Base is properly configured
        if hasattr(Base, 'metadata'):
            print("✅ Base.metadata exists")
        else:
            print("❌ Base.metadata missing")
            return False
        
        # Check if it's the new DeclarativeBase pattern
        if hasattr(Base, '__mro__') and any('DeclarativeBase' in str(cls) for cls in Base.__mro__):
            print("✅ Base uses SQLAlchemy 2.x DeclarativeBase pattern")
        else:
            print("⚠️ Base may not be using DeclarativeBase pattern")
        
        # Check metadata naming conventions
        if hasattr(Base.metadata, 'naming_convention'):
            print("✅ Enterprise naming conventions configured")
            conventions = Base.metadata.naming_convention
            required_conventions = ['ix', 'uq', 'ck', 'fk', 'pk']
            for conv in required_conventions:
                if conv in conventions:
                    print(f"  ✅ {conv}: {conventions[conv]}")
                else:
                    print(f"  ❌ Missing convention: {conv}")
                    return False
        else:
            print("❌ Naming conventions not configured")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Base class structure test failed: {e}")
        return False

def test_metadata_schema_property():
    """Test that metadata schema property issue is resolved."""
    print("\n🔍 Testing Metadata Schema Property Access...")
    
    try:
        from app.core.database import Base, metadata
        
        # Test metadata access patterns
        print(f"✅ metadata object: {type(metadata)}")
        
        # Test the problematic schema property access
        try:
            schema_value = metadata.schema
            print(f"✅ metadata.schema accessible: {schema_value}")
        except AttributeError as e:
            if "'property' object has no attribute 'schema'" in str(e):
                print("❌ CRITICAL: Still has metadata schema property issue")
                return False
            else:
                print(f"⚠️ Different metadata issue: {e}")
        
        # Test Base metadata access
        try:
            base_metadata = Base.metadata
            print(f"✅ Base.metadata accessible: {type(base_metadata)}")
        except Exception as e:
            print(f"❌ Base.metadata access failed: {e}")
            return False
        
        # Test metadata tables access (this is where the error often occurs)
        try:
            tables = Base.metadata.tables
            print(f"✅ Base.metadata.tables accessible: {len(tables)} tables")
        except Exception as e:
            print(f"❌ Base.metadata.tables access failed: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Metadata schema property test failed: {e}")
        return False

def test_model_loading():
    """Test loading of all models with the new architecture."""
    print("\n📊 Testing Model Loading with SQLAlchemy 2.x...")
    
    model_modules = [
        "app.models.user",
        "app.models.trading", 
        "app.models.credit",
        "app.models.exchange"
    ]
    
    loaded_models = 0
    total_models = len(model_modules)
    
    for module_name in model_modules:
        try:
            module = __import__(module_name, fromlist=[''])
            print(f"✅ {module_name} loaded successfully")
            loaded_models += 1
            
            # Check for models in the module
            import inspect
            model_classes = [
                name for name, obj in inspect.getmembers(module, inspect.isclass)
                if hasattr(obj, '__tablename__')
            ]
            if model_classes:
                print(f"  📋 Found models: {', '.join(model_classes)}")
            
        except Exception as e:
            print(f"❌ {module_name} failed to load: {e}")
    
    success_rate = (loaded_models / total_models) * 100
    print(f"\n📊 Model Loading Results: {loaded_models}/{total_models} ({success_rate:.1f}%)")
    
    return loaded_models == total_models

def test_trading_strategy_model():
    """Specifically test the TradingStrategy model that was causing the error."""
    print("\n🎯 Testing TradingStrategy Model (Error Source)...")
    
    try:
        from app.models.trading import TradingStrategy
        print("✅ TradingStrategy model imported successfully")
        
        # Test model attributes
        if hasattr(TradingStrategy, '__tablename__'):
            print(f"✅ TradingStrategy.__tablename__: {TradingStrategy.__tablename__}")
        else:
            print("❌ TradingStrategy missing __tablename__")
            return False
        
        # Test metadata access (this was the failing point)
        try:
            model_metadata = TradingStrategy.metadata
            print(f"✅ TradingStrategy.metadata accessible: {type(model_metadata)}")
        except Exception as e:
            print(f"❌ TradingStrategy.metadata access failed: {e}")
            return False
        
        # Test table access
        try:
            table = TradingStrategy.__table__
            print(f"✅ TradingStrategy.__table__ accessible: {table.name}")
        except Exception as e:
            print(f"❌ TradingStrategy.__table__ access failed: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ TradingStrategy model test failed: {e}")
        print(f"   This is the exact error that was preventing backend startup!")
        return False

def test_enterprise_features():
    """Test enterprise features of the new architecture."""
    print("\n🏆 Testing Enterprise Features...")
    
    try:
        from app.core.database import Base
        
        # Test naming conventions
        if hasattr(Base.metadata, 'naming_convention'):
            conventions = Base.metadata.naming_convention
            print("✅ Enterprise naming conventions:")
            for key, value in conventions.items():
                print(f"  {key}: {value}")
        else:
            print("❌ Enterprise naming conventions missing")
            return False
        
        # Test enterprise base features
        if hasattr(Base, '__tablename__'):
            print("✅ Automatic table naming available")
        else:
            print("⚠️ Automatic table naming not configured")
        
        return True
        
    except Exception as e:
        print(f"❌ Enterprise features test failed: {e}")
        return False

def test_backward_compatibility():
    """Test that existing code patterns still work."""
    print("\n🔄 Testing Backward Compatibility...")
    
    try:
        # Test old import patterns still work
        from app.core.database import metadata, Base
        
        # Test metadata access (old pattern)
        print(f"✅ metadata variable accessible: {type(metadata)}")
        
        # Test Base access (old pattern)
        print(f"✅ Base variable accessible: {type(Base)}")
        
        # Test that old patterns don't break
        try:
            tables = metadata.tables
            print(f"✅ metadata.tables accessible: {len(tables)} tables")
        except Exception as e:
            print(f"❌ metadata.tables access failed: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        return False

def main():
    """Run all SQLAlchemy 2.x fix validation tests."""
    print("🚀 Enterprise SQLAlchemy 2.x Fix Validation")
    print("=" * 60)
    
    tests = [
        ("Database Architecture Imports", test_database_imports),
        ("SQLAlchemy 2.x Base Class Structure", test_base_class_structure),
        ("Metadata Schema Property Fix", test_metadata_schema_property),
        ("Model Loading", test_model_loading),
        ("TradingStrategy Model (Error Source)", test_trading_strategy_model),
        ("Enterprise Features", test_enterprise_features),
        ("Backward Compatibility", test_backward_compatibility)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED\n")
            else:
                print(f"❌ {test_name}: FAILED\n")
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}\n")
    
    print("=" * 60)
    print(f"📊 SQLAlchemy 2.x Fix Results: {passed}/{total} tests passed")
    print(f"🎯 Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("🏆 SQLAlchemy 2.x Enterprise Architecture Fix SUCCESSFUL!")
        print("\n✅ The metadata schema property issue is RESOLVED")
        print("✅ Backend should now start without SQLAlchemy errors")
        print("✅ All models should load correctly")
        print("✅ Enterprise patterns implemented")
        return 0
    elif passed >= total - 1:
        print("\n⚠️ MOSTLY SUCCESSFUL - Minor issues remain")
        print("🔧 SQLAlchemy 2.x fix is working but needs minor adjustments")
        return 1
    else:
        print("\n❌ SIGNIFICANT ISSUES REMAIN")
        print("🚨 SQLAlchemy 2.x fix needs more work")
        return 2

if __name__ == "__main__":
    sys.exit(main())