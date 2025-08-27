#!/bin/bash
# Direct build script that avoids setuptools.build_meta issues
set -e

echo "🚀 Starting CryptoUniverse Enterprise Build..."

# Upgrade pip and install essential build tools
echo "📦 Installing build essentials..."
pip install --upgrade pip
pip install --no-build-isolation setuptools>=68.0.0 wheel>=0.40.0 packaging

# Install packages one by one to isolate any problematic ones
echo "📦 Installing core dependencies..."

# Install FastAPI and web framework dependencies first
pip install --no-build-isolation fastapi==0.104.1
pip install --no-build-isolation uvicorn[standard]==0.24.0

# Install database dependencies
pip install --no-build-isolation sqlalchemy==2.0.23
pip install --no-build-isolation alembic==1.13.1
pip install --no-build-isolation asyncpg==0.29.0

# Install auth dependencies
pip install --no-build-isolation python-jose[cryptography]==3.3.0
pip install --no-build-isolation passlib[bcrypt]==1.7.4
pip install --no-build-isolation python-multipart==0.0.6

# Install validation dependencies
pip install --no-build-isolation pydantic==2.5.1
pip install --no-build-isolation pydantic-settings==2.1.0

# Install HTTP client dependencies
pip install --no-build-isolation httpx==0.25.2
pip install --no-build-isolation aiohttp==3.9.1

# Install background task dependencies
pip install --no-build-isolation celery==5.3.4
pip install --no-build-isolation redis==5.0.1

# Install other dependencies
pip install --no-build-isolation stripe==7.8.0
pip install --no-build-isolation structlog==23.2.0
pip install --no-build-isolation sentry-sdk[fastapi]==1.38.0
pip install --no-build-isolation python-dotenv==1.0.0
pip install --no-build-isolation websockets==12.0

# Install remaining dependencies
pip install --no-build-isolation bcrypt==4.1.2
pip install --no-build-isolation PyJWT==2.8.0
pip install --no-build-isolation cryptography==41.0.7
pip install --no-build-isolation email-validator==2.1.0
pip install --no-build-isolation aiofiles==23.2.1
pip install --no-build-isolation typing-extensions==4.8.0
pip install --no-build-isolation pytz==2023.3
pip install --no-build-isolation psutil==5.9.6
pip install --no-build-isolation setproctitle==1.3.3
pip install --no-build-isolation gunicorn==21.2.0

# Install scientific packages (these often cause setuptools.build_meta issues)
echo "📊 Installing scientific packages..."
pip install --no-build-isolation numpy==1.24.3
pip install --no-build-isolation pandas==2.0.3

# Install crypto and AI packages last
echo "🤖 Installing crypto and AI packages..."
pip install --no-build-isolation ccxt==4.2.25
pip install --no-build-isolation openai==1.3.8
pip install --no-build-isolation anthropic==0.7.8

echo "🎉 Build completed successfully!"
echo "All packages installed without setuptools.build_meta errors."
