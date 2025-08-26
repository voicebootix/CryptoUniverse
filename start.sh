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

# Calculate workers based on available CPU cores
if [ -z "$WEB_CONCURRENCY" ]; then
    # Use 2 workers per core, with a minimum of 2 and maximum of 8
    WORKERS=$(python -c "
import os
import multiprocessing

cores = multiprocessing.cpu_count()
workers = min(max(cores * 2, 2), 8)
print(workers)
")
    export WEB_CONCURRENCY=$WORKERS
fi

echo "🔧 Configuration:"
echo "  Workers: $WEB_CONCURRENCY"
echo "  Port: $PORT"
echo "  Environment: $ENVIRONMENT"

# Start the application with optimized settings
echo "🎉 Starting Gunicorn server..."

exec gunicorn main:app \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${WEB_CONCURRENCY:-4} \
    --worker-class uvicorn.workers.UvicornWorker \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --timeout 120 \
    --keep-alive 2 \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --capture-output \
    --enable-stdio-inheritance
