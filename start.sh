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
import random
import time
import traceback
from typing import Optional, Tuple
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.database import create_ssl_context


def parse_bool(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


async def tcp_probe(host: str, port: int, timeout: float) -> Tuple[bool, Optional[BaseException]]:
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
    except BaseException as exc:  # noqa: BLE001 - surface any failure
        return False, exc

    writer.close()
    try:
        await writer.wait_closed()
    except Exception:  # noqa: BLE001 - ignore close errors during probe
        pass
    return True, None


async def wait_for_db() -> bool:
    settings = get_settings()
    database_url = (settings.DATABASE_URL or os.getenv("DATABASE_URL") or "").strip()
    if not database_url:
        print("❌ DATABASE_URL not set")
        return False

    parsed = urlparse(database_url)

    ssl_required = (
        parse_bool(os.getenv("DATABASE_SSL_REQUIRE"))
        or getattr(settings, "DATABASE_SSL_REQUIRE", False)
        or getattr(settings, "DATABASE_SSL_ROOT_CERT", None) is not None
        or "sslmode=require" in database_url
        or "supabase" in database_url.lower()
    )

    ssl_context = None
    if ssl_required:
        try:
            ssl_context = create_ssl_context()
            print("🔐 SSL context initialized for database connection")
        except Exception as ssl_error:
            print(f"❌ Failed to create SSL context: {ssl_error}")
            traceback.print_exc()
            return False
    else:
        print("ℹ️ Database SSL not required by configuration")

    max_attempts = int(os.getenv("DB_MAX_ATTEMPTS", "15"))
    base_connect_timeout = float(os.getenv("DB_CONNECT_TIMEOUT", "10"))
    max_connect_timeout = float(os.getenv("DB_MAX_CONNECT_TIMEOUT", "30"))
    command_timeout = float(os.getenv("DB_COMMAND_TIMEOUT", "30"))
    max_retry_delay = float(os.getenv("DB_MAX_RETRY_DELAY", "30"))
    tcp_probe_timeout = float(os.getenv("DB_TCP_TIMEOUT", "3"))
    warm_pool = parse_bool(os.getenv("DB_WARM_POOL", "true"))
    pool_min_size = int(os.getenv("DB_POOL_MIN_SIZE", "1"))
    pool_max_size = int(os.getenv("DB_POOL_MAX_SIZE", "5"))

    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    target_details = {
        "host": host,
        "port": port,
        "database": (parsed.path.lstrip("/") or "(default)") if parsed.path else "(default)",
        "ssl": "enabled" if ssl_context else "disabled",
    }
    print(
        "🔎 Database target:",
        ", ".join(f"{key}={value}" for key, value in target_details.items()),
    )

    for attempt in range(1, max_attempts + 1):
        connect_timeout = min(base_connect_timeout + (attempt - 1) * 5, max_connect_timeout)
        start_time = time.monotonic()
        tcp_ok, tcp_error = await tcp_probe(host, port, tcp_probe_timeout)
        if not tcp_ok:
            elapsed = time.monotonic() - start_time
            print(
                f"🚫 Database port probe failed ({elapsed:.2f}s) on attempt "
                f"{attempt}/{max_attempts}: {type(tcp_error).__name__}: {tcp_error}"
            )
            if attempt == max_attempts:
                break

            delay = min(max_retry_delay, (2 ** (attempt - 1)) + random.uniform(0, 1))
            await asyncio.sleep(delay)
            continue
        try:
            conn = await asyncpg.connect(
                database_url,
                ssl=ssl_context,
                timeout=connect_timeout,
                command_timeout=command_timeout,
                server_settings={"application_name": "cryptouniverse_startup"},
            )
            await conn.execute("SELECT 1")
            await conn.close()
            if warm_pool:
                pool = None
                try:
                    pool = await asyncpg.create_pool(
                        database_url,
                        ssl=ssl_context,
                        min_size=pool_min_size,
                        max_size=pool_max_size,
                        command_timeout=command_timeout,
                        timeout=connect_timeout,
                        server_settings={"application_name": "cryptouniverse_startup_pool"},
                    )
                    async with pool.acquire() as pooled_conn:
                        await pooled_conn.execute("SELECT 1")
                except Exception as pool_exc:  # noqa: BLE001
                    print(
                        "⚠️ Database pool warm-up failed: "
                        f"{type(pool_exc).__name__}: {pool_exc}"
                    )
                else:
                    print(
                        "💠 Database pool warm-up successful "
                        f"(min_size={pool_min_size}, max_size={pool_max_size})"
                    )
                finally:
                    if pool is not None:
                        await pool.close()
            elapsed = time.monotonic() - start_time
            print(
                f"✅ Database connection successful after {elapsed:.2f}s "
                f"(attempt {attempt}/{max_attempts})"
            )
            return True
        except Exception as exc:
            elapsed = time.monotonic() - start_time
            error_type = type(exc).__name__
            module = type(exc).__module__
            if module and module != "builtins":
                error_type = f"{module}.{error_type}"
            error_message = str(exc) or repr(exc)
            print(
                f"🔄 Database connection attempt {attempt}/{max_attempts} failed "
                f"({elapsed:.2f}s): {error_type}: {error_message}"
            )
            if attempt == max_attempts:
                break

            delay = min(max_retry_delay, (2 ** (attempt - 1)) + random.uniform(0, 1))
            await asyncio.sleep(delay)

    print("❌ Failed to connect to database after all attempts")
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
