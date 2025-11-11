import os
import sys
from pathlib import Path
import asyncio

import pytest

# Configure environment before importing application modules
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "True"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ENCRYPTION_KEY"] = "V6fVaBkH6LxlYccfo-XII2p4HbAbH8iQJ5vr_bx0jPA="
os.environ.setdefault("ALLOWED_HOSTS", "testserver,localhost,127.0.0.1")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# Ensure previous test database is removed to avoid stale state
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

Path("test.db").unlink(missing_ok=True)

from app.core.database import Base, AsyncSessionLocal, engine  # noqa: E402
from app.db.seeds import seed_core_data  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await session.run_sync(seed_core_data)
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    Path("test.db").unlink(missing_ok=True)


@pytest.fixture(scope="session")
def client(setup_database: None) -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
