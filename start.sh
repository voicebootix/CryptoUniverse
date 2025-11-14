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
    python - <<'PYTHON'
import asyncio
import asyncpg
import os


async def wait_for_db() -> bool:
    """Simple database connection check - matches old working code exactly."""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print('❌ DATABASE_URL not set')
        return False
    
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            # OLD WORKING CODE: Simple connection, no SSL context, no timeouts, no TCP probe
            # This is what worked before all the "optimizations"
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


if __name__ == "__main__":
    success = asyncio.run(wait_for_db())
    raise SystemExit(0 if success else 1)
PYTHON
    if [ $? -ne 0 ]; then
        echo "❌ Database connection failed"
        return 1
    fi

    return 0
}

# Function to wait for Redis
wait_for_redis() {
    echo "⏳ Waiting for Redis connection..."
    python - <<'PYTHON'
import os
import random
import ssl
import time
from typing import Optional
from urllib.parse import urlparse

import redis

from app.core.config import get_settings


def parse_bool(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def wait_for_redis() -> bool:
    settings = get_settings()
    redis_url = (os.getenv("REDIS_URL") or getattr(settings, "REDIS_URL", "")).strip()

    redis_optional = parse_bool(os.getenv("REDIS_OPTIONAL"))

    if not redis_url:
        if redis_optional:
            print("⚠️ REDIS_URL not configured but Redis marked optional; skipping readiness check")
            return True

        print("❌ REDIS_URL not set")
        return False

    parsed = urlparse(redis_url)
    scheme = (parsed.scheme or "redis").lower()

    ssl_required = scheme in {"rediss", "redis+ssl"} or parse_bool(os.getenv("REDIS_SSL_REQUIRE"))
    ssl_insecure = parse_bool(os.getenv("REDIS_SSL_INSECURE"))
    ssl_ca_file = os.getenv("REDIS_SSL_ROOT_CERT") or os.getenv("REDIS_SSL_CA_FILE")

    if ssl_required:
        print("🔐 Redis SSL/TLS required for connection")
        if ssl_insecure:
            print("   ⚠️ TLS certificate verification disabled for Redis (REDIS_SSL_INSECURE)")
        elif ssl_ca_file:
            print(f"   📁 Using Redis CA bundle from {ssl_ca_file}")

    max_attempts = int(os.getenv("REDIS_MAX_ATTEMPTS", "20"))
    base_connect_timeout = float(os.getenv("REDIS_CONNECT_TIMEOUT", "5"))
    max_connect_timeout = float(os.getenv("REDIS_MAX_CONNECT_TIMEOUT", "20"))
    command_timeout = float(os.getenv("REDIS_COMMAND_TIMEOUT", "5"))
    base_delay = float(os.getenv("REDIS_BASE_DELAY", "1"))
    max_retry_delay = float(os.getenv("REDIS_MAX_RETRY_DELAY", "15"))

    target_details = {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or (6380 if scheme in {"rediss", "redis+ssl"} else 6379),
        "ssl": "enabled" if ssl_required else "disabled",
    }
    print(
        "🔎 Redis target:",
        ", ".join(f"{key}={value}" for key, value in target_details.items()),
    )

    for attempt in range(1, max_attempts + 1):
        connect_timeout = min(base_connect_timeout + (attempt - 1) * 1.5, max_connect_timeout)
        start_time = time.monotonic()

        try:
            connection_kwargs = {
                "socket_connect_timeout": connect_timeout,
                "socket_timeout": command_timeout,
                "retry_on_timeout": True,
                "health_check_interval": 10,
            }

            if ssl_required:
                connection_kwargs["connection_class"] = redis.connection.SSLConnection
                connection_kwargs["ssl_cert_reqs"] = (
                    ssl.CERT_NONE if ssl_insecure else ssl.CERT_REQUIRED
                )
                if ssl_ca_file and not ssl_insecure:
                    connection_kwargs["ssl_ca_certs"] = ssl_ca_file

            client = redis.from_url(
                redis_url,
                **connection_kwargs,
            )

            client.ping()
        except Exception as exc:  # noqa: BLE001 - surface any failure
            elapsed = time.monotonic() - start_time
            error_type = type(exc).__name__
            module = type(exc).__module__
            if module and module != "builtins":
                error_type = f"{module}.{error_type}"

            print(
                f"🔄 Redis connection attempt {attempt}/{max_attempts} failed "
                f"({elapsed:.2f}s): {error_type}: {exc}"
            )

            if attempt == max_attempts:
                break

            delay = min(
                max_retry_delay,
                base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.75),
            )
            time.sleep(delay)
            continue

        else:
            elapsed = time.monotonic() - start_time
            print(
                f"✅ Redis connection successful after {elapsed:.2f}s "
                f"(attempt {attempt}/{max_attempts})"
            )
            try:
                client.close()
            except Exception:
                pass
            return True

    print("❌ Failed to connect to Redis after all attempts")

    if redis_optional:
        print("⚠️ Continuing startup without Redis because REDIS_OPTIONAL is enabled")
        return True

    return False


if __name__ == "__main__":
    success = wait_for_redis()
    raise SystemExit(0 if success else 1)
PYTHON
    if [ $? -ne 0 ]; then
        echo "❌ Redis connection failed"
        return 1
    fi

    return 0
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

# Wait for dependencies in parallel
wait_for_db &
DB_PID=$!
wait_for_redis &
REDIS_PID=$!

set +e
wait "$DB_PID"
DB_STATUS=$?
wait "$REDIS_PID"
REDIS_STATUS=$?
set -e

if [ "$DB_STATUS" -ne 0 ]; then
    echo "❌ Database readiness checks failed"
    exit "$DB_STATUS"
fi

if [ "$REDIS_STATUS" -ne 0 ]; then
    echo "❌ Redis readiness checks failed"
    exit "$REDIS_STATUS"
fi

# Run migrations in production
if [ "$ENVIRONMENT" = "production" ]; then
    run_migrations
fi

# Derive optimal runtime settings from configuration helper
RUNTIME_HINTS_RAW="$(python - <<'PYTHON'
from app.core.config import settings

print(settings.recommended_web_concurrency)
print(settings.memory_limit_mb or "")
print(settings.GUNICORN_TIMEOUT)
print(settings.GUNICORN_GRACEFUL_TIMEOUT)
print(settings.GUNICORN_KEEPALIVE)
print(settings.GUNICORN_MAX_REQUESTS)
print(settings.GUNICORN_MAX_REQUESTS_JITTER)
PYTHON
)" || {
    echo "❌ Failed to derive runtime hints from app.core.config" >&2
    exit 1
}
readarray -t RUNTIME_HINTS <<<"$RUNTIME_HINTS_RAW"

AUTO_WORKERS=${RUNTIME_HINTS[0]:-1}
AUTO_MEMORY_LIMIT=${RUNTIME_HINTS[1]:-}
AUTO_TIMEOUT=${RUNTIME_HINTS[2]:-180}
AUTO_GRACEFUL_TIMEOUT=${RUNTIME_HINTS[3]:-180}
AUTO_KEEPALIVE=${RUNTIME_HINTS[4]:-2}
AUTO_MAX_REQUESTS=${RUNTIME_HINTS[5]:-1000}
AUTO_MAX_REQUESTS_JITTER=${RUNTIME_HINTS[6]:-100}

if [ -z "$WEB_CONCURRENCY" ] || ! [[ "$WEB_CONCURRENCY" =~ ^[0-9]+$ ]] || [ "$WEB_CONCURRENCY" -lt 1 ]; then
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
