#!/bin/bash
# Custom build script for CryptoUniverse Enterprise
# Handles setuptools.build_meta issues properly

set -e

echo "🚀 Starting CryptoUniverse Enterprise Build..."

# Upgrade pip first
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install build requirements first (this includes setuptools)
echo "🔧 Installing build requirements..."
pip install -r build-requirements.txt

# Verify setuptools is properly installed
echo "✅ Verifying setuptools installation..."
python -c "
import setuptools
import setuptools.build_meta
print(f'✅ setuptools version: {setuptools.__version__}')
print('✅ setuptools.build_meta is available and working')

# Test that we can actually use it
try:
    from setuptools.build_meta import build_wheel, build_sdist
    print('✅ setuptools.build_meta functions are importable')
except ImportError as e:
    print(f'❌ setuptools.build_meta functions not available: {e}')
    exit(1)
"

# Install main requirements
echo "📦 Installing main requirements..."
pip install -r requirements.txt

echo "🎉 Build completed successfully!"
echo "setuptools.build_meta error has been resolved."
