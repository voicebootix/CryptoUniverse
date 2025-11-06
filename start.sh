#!/bin/bash

# CryptoUniverse Enterprise - Production Start Script
# Optimized for Render.com deployment

set -e  # Exit on error

echo "🚀 Starting CryptoUniverse Enterprise..."
echo "Environment: $ENVIRONMENT"
echo "Port: $PORT"

# Function to wait for database
wait_for_db() {
    echo "⏳ Waiting for database connection..."
    python -c "
import asyncio
import asyncpg
import os
import time
from urllib.parse import urlparse

async def wait_for_db():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print('❌ DATABASE_URL not set')
        return False
    
    parsed = urlparse(database_url)
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            conn = await asyncpg.connect(database_url)
            await conn.execute('SELECT 1')
            await conn.close()
            print('✅ Database connection successful')
            return True
        except Exception as e:
            attempt += 1
            print(f'🔄 Database connection attempt {attempt}/{max_attempts} failed: {e}')
            await asyncio.sleep(2)
    
    print('❌ Failed to connect to database after all attempts')
    return False

asyncio.run(wait_for_db())
"
    if [ $? -ne 0 ]; then
        echo "❌ Database connection failed"
        exit 1
    fi
}

# Function to wait for Redis
wait_for_redis() {
    echo "⏳ Waiting for Redis connection..."
    python -c "
import redis
import os
import time
from urllib.parse import urlparse

def wait_for_redis():
    redis_url = os.getenv('REDIS_URL')
    if not redis_url:
        print('❌ REDIS_URL not set')
        return False
    
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            r = redis.from_url(redis_url)
            r.ping()
            print('✅ Redis connection successful')
            return True
        except Exception as e:
            attempt += 1
            print(f'🔄 Redis connection attempt {attempt}/{max_attempts} failed: {e}')
            time.sleep(2)
    
    print('❌ Failed to connect to Redis after all attempts')
    return False

wait_for_redis()
"
    if [ $? -ne 0 ]; then
        echo "❌ Redis connection failed"
        exit 1
    fi
}

# Function to run database migrations
run_migrations() {
    echo "📊 Running database migrations..."
    if [ -f "alembic.ini" ]; then
        alembic upgrade head
        echo "✅ Database migrations completed"
    else
        echo "⚠️ No alembic.ini found, skipping migrations"
    fi
}

# Pre-flight checks
echo "🔍 Running pre-flight checks..."

# Wait for dependencies
wait_for_db
wait_for_redis

# Run migrations in production
if [ "$ENVIRONMENT" = "production" ]; then
    run_migrations
fi

# Derive optimal runtime settings from configuration helper
mapfile -t RUNTIME_HINTS < <(python - <<'PYTHON'
from app.core.config import settings

print(settings.recommended_web_concurrency)
print(settings.memory_limit_mb or "")
print(settings.GUNICORN_TIMEOUT)
print(settings.GUNICORN_GRACEFUL_TIMEOUT)
print(settings.GUNICORN_KEEPALIVE)
print(settings.GUNICORN_MAX_REQUESTS)
print(settings.GUNICORN_MAX_REQUESTS_JITTER)
PYTHON
)

AUTO_WORKERS=${RUNTIME_HINTS[0]:-1}
AUTO_MEMORY_LIMIT=${RUNTIME_HINTS[1]}
AUTO_TIMEOUT=${RUNTIME_HINTS[2]:-180}
AUTO_GRACEFUL_TIMEOUT=${RUNTIME_HINTS[3]:-180}
AUTO_KEEPALIVE=${RUNTIME_HINTS[4]:-2}
AUTO_MAX_REQUESTS=${RUNTIME_HINTS[5]:-1000}
AUTO_MAX_REQUESTS_JITTER=${RUNTIME_HINTS[6]:-100}

if [ -z "$WEB_CONCURRENCY" ] || [ "$WEB_CONCURRENCY" -lt 1 ]; then
    WEB_CONCURRENCY=$AUTO_WORKERS
fi

if [ -z "$GUNICORN_TIMEOUT" ]; then
    GUNICORN_TIMEOUT=$AUTO_TIMEOUT
fi

if [ -z "$GUNICORN_GRACEFUL_TIMEOUT" ]; then
    GUNICORN_GRACEFUL_TIMEOUT=$AUTO_GRACEFUL_TIMEOUT
fi

if [ -z "$GUNICORN_KEEPALIVE" ]; then
    GUNICORN_KEEPALIVE=$AUTO_KEEPALIVE
fi

if [ -z "$GUNICORN_MAX_REQUESTS" ]; then
    GUNICORN_MAX_REQUESTS=$AUTO_MAX_REQUESTS
fi

if [ -z "$GUNICORN_MAX_REQUESTS_JITTER" ]; then
    GUNICORN_MAX_REQUESTS_JITTER=$AUTO_MAX_REQUESTS_JITTER
fi

export WEB_CONCURRENCY
export GUNICORN_TIMEOUT
export GUNICORN_GRACEFUL_TIMEOUT
export GUNICORN_KEEPALIVE
export GUNICORN_MAX_REQUESTS
export GUNICORN_MAX_REQUESTS_JITTER

echo "🔧 Configuration:"
echo "  Workers: $WEB_CONCURRENCY"
if [ -n "$AUTO_MEMORY_LIMIT" ]; then
    echo "  Memory limit: ${AUTO_MEMORY_LIMIT} MB"
else
    echo "  Memory limit: not detected"
fi
echo "  Timeout: ${GUNICORN_TIMEOUT}s (graceful ${GUNICORN_GRACEFUL_TIMEOUT}s)"
echo "  Port: $PORT"
echo "  Environment: $ENVIRONMENT"

# Start the application with optimized settings
echo "🎉 Starting Gunicorn server..."

exec gunicorn main:app \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${WEB_CONCURRENCY:-1} \
    --worker-class uvicorn.workers.UvicornWorker \
    --worker-connections 1000 \
    --max-requests ${GUNICORN_MAX_REQUESTS} \
    --max-requests-jitter ${GUNICORN_MAX_REQUESTS_JITTER} \
    --timeout ${GUNICORN_TIMEOUT} \
    --graceful-timeout ${GUNICORN_GRACEFUL_TIMEOUT} \
    --keep-alive ${GUNICORN_KEEPALIVE} \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --capture-output \
    --enable-stdio-inheritance
