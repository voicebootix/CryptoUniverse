#!/usr/bin/env python
"""
Test script to debug Render environment
"""
import sys
import os

print("=" * 50)
print("RENDER ENVIRONMENT DEBUG")
print("=" * 50)

print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Current directory: {os.getcwd()}")
print(f"Environment: {os.environ.get('ENVIRONMENT', 'not set')}")
print(f"Port: {os.environ.get('PORT', 'not set')}")

print("\nTrying to import setuptools...")
try:
    import setuptools
    print(f"✅ setuptools version: {setuptools.__version__}")
    
    try:
        import setuptools.build_meta
        print("✅ setuptools.build_meta is available")
    except ImportError as e:
        print(f"❌ setuptools.build_meta not available: {e}")
except ImportError as e:
    print(f"❌ setuptools not available: {e}")

print("\nTrying to import pip...")
try:
    import pip
    print(f"✅ pip version: {pip.__version__}")
except:
    print("❌ pip not available as module")

print("\nInstalled packages:")
os.system("pip list | head -20")

print("\n" + "=" * 50)
print("Starting ultra-minimal FastAPI app...")
print("=" * 50)

# Now run the minimal app
exec(open('app-minimal.py').read())
