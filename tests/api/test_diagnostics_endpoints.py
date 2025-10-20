import os
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from starlette.requests import Request
from starlette.responses import Response

# Ensure required configuration values exist before importing application modules.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")

from app.api.v1.endpoints import diagnostics  # noqa: E402  pylint: disable=wrong-import-position
from app.middleware.auth import AuthMiddleware  # noqa: E402  pylint: disable=wrong-import-position


class _DummySession:
    async def __aenter__(self):  # pragma: no cover - exercised via async context
        return self

    async def __aexit__(self, exc_type, exc, tb):  # pragma: no cover - exercised via async context
        return False

    async def execute(self, _query):
        return None


class _DummySessionFactory:
    def __call__(self):
        return _DummySession()


class _DummyRedis:
    async def ping(self):
        return True


def _make_request(method: str, path: str, headers: Dict[str, str] | None = None) -> Request:
    """Create a Starlette request object suitable for invoking endpoint callables."""
    header_items: Iterable[Tuple[bytes, bytes]] = (
        (k.lower().encode("latin-1"), v.encode("latin-1"))
        for k, v in (headers or {}).items()
    )

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": list(header_items),
        "client": ("127.0.0.1", 12345),
        "query_string": b"",
        "server": ("testserver", 80),
    }

    async def receive():
        return {"type": "http.request"}

    request = Request(scope, receive)
    request.state._start_time = time.perf_counter()  # Emulate logging middleware state
    return request


@pytest.fixture(autouse=True)
def _stub_database(monkeypatch):
    monkeypatch.setattr(diagnostics, "AsyncSessionLocal", _DummySessionFactory())


@pytest.fixture
def _stub_redis(monkeypatch):
    async def _get_client():
        return _DummyRedis()

    monkeypatch.setattr(diagnostics, "get_redis_client", _get_client)
    monkeypatch.setattr(diagnostics.rate_limiter, "redis", object())


@pytest.fixture
def _stub_rate_limiter(monkeypatch):
    async def _check_rate_limit(*_args, **_kwargs):
        return True

    monkeypatch.setattr(diagnostics.rate_limiter, "check_rate_limit", _check_rate_limit)


@pytest.fixture
def _stub_auth_service(monkeypatch):
    class _DummyAuthService:
        def verify_password(self, *_args, **_kwargs):
            return True

        def create_access_token(self, *_args, **_kwargs):
            return "token"

        def create_refresh_token(self, *_args, **_kwargs):
            return "refresh"

    monkeypatch.setattr("app.api.v1.endpoints.auth.auth_service", _DummyAuthService())


@pytest.mark.asyncio
async def test_test_layers_reports_all_layers_healthy(_stub_redis, _stub_rate_limiter):
    request = _make_request("GET", "/api/v1/diagnostics/test-layers", {"accept": "application/json"})

    result = await diagnostics.test_middleware_layers(request)

    assert result["overall"]["health"] == "healthy"
    assert result["layers"]["database"]["status"] == "passed"
    assert result["layers"]["redis"]["status"] == "passed"
    assert result["layers"]["rate_limit_check"]["result"] == "allowed"
    assert result["layers"]["auth_middleware"]["status"] == "not_authenticated"


@pytest.mark.asyncio
async def test_test_login_flow_identifies_success_path(_stub_rate_limiter, _stub_auth_service):
    request = _make_request("POST", "/api/v1/diagnostics/test-login-flow")

    trace = await diagnostics.test_login_flow(request)

    assert trace["success"] is True
    assert trace["failed_steps"] == []
    step_names = {step["name"] for step in trace["steps"]}
    assert {"request_received", "rate_limit_check", "database_query", "auth_service"}.issubset(step_names)


@pytest.mark.asyncio
async def test_auth_middleware_skips_public_diagnostics_path():
    request = _make_request("GET", "/api/v1/diagnostics/test-layers")

    class _DummyApp:
        async def __call__(self, scope, receive, send):  # pragma: no cover - required by BaseHTTPMiddleware
            pass

    middleware = AuthMiddleware(_DummyApp())

    called = {"value": False}

    async def _call_next(req):
        called["value"] = True
        return Response("ok", media_type="text/plain")

    response = await middleware.dispatch(request, _call_next)

    assert called["value"] is True
    assert response.status_code == 200
    assert response.body == b"ok"

