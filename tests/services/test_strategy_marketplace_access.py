from contextlib import asynccontextmanager
from pathlib import Path
import sys
import uuid

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

pytest.importorskip("aiosqlite")

sys.path.append(str(Path(__file__).resolve().parents[2]))


if not hasattr(SQLiteTypeCompiler, "visit_UUID"):
    def _visit_uuid(_, __, **_kw):  # pragma: no cover - sqlite shim
        return "CHAR(36)"

    SQLiteTypeCompiler.visit_UUID = _visit_uuid  # type: ignore[attr-defined]

if not hasattr(SQLiteTypeCompiler, "visit_JSONB"):
    def _visit_jsonb(self, _type, **_kw):  # pragma: no cover - sqlite shim
        return "JSON"

    SQLiteTypeCompiler.visit_JSONB = _visit_jsonb  # type: ignore[attr-defined]


@pytest_asyncio.fixture()
async def marketplace_env(tmp_path, monkeypatch):
    db_path = tmp_path / "marketplace_access.db"
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")

    global redis_module
    global marketplace_module
    global StrategyMarketplaceService
    global CreditAccount
    global UserStrategyAccess
    global StrategyAccessType
    global StrategyType
    global User
    global UserRole

    from app.core import redis as redis_module  # type: ignore[assignment]
    from app.models.credit import CreditAccount as CreditAccountModel
    from app.models.strategy_access import (
        StrategyAccessType as StrategyAccessTypeEnum,
        StrategyType as StrategyTypeEnum,
        UserStrategyAccess as UserStrategyAccessModel,
    )
    from app.models.user import User as UserModel, UserRole as UserRoleEnum
    from app.services import strategy_marketplace_service as marketplace_module  # type: ignore[assignment]
    from app.services.strategy_marketplace_service import (
        StrategyMarketplaceService as StrategyMarketplaceServiceCls,
    )

    CreditAccount = CreditAccountModel
    UserStrategyAccess = UserStrategyAccessModel
    StrategyAccessType = StrategyAccessTypeEnum
    StrategyType = StrategyTypeEnum
    User = UserModel
    UserRole = UserRoleEnum
    StrategyMarketplaceService = StrategyMarketplaceServiceCls
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(sa.text("PRAGMA foreign_keys=OFF"))
        await conn.run_sync(User.__table__.create, checkfirst=True)
        await conn.run_sync(CreditAccount.__table__.create, checkfirst=True)
        await conn.run_sync(UserStrategyAccess.__table__.create, checkfirst=True)

    @asynccontextmanager
    async def _session_ctx():
        async with SessionLocal() as session:
            yield session

    async def _no_redis():
        return None

    monkeypatch.setattr(marketplace_module, "get_database_session", _session_ctx)
    monkeypatch.setattr(redis_module, "get_redis_client", _no_redis)

    service = StrategyMarketplaceService()
    try:
        yield service, SessionLocal
    finally:
        await engine.dispose()


async def _create_user_with_account(session) -> uuid.UUID:
    user = User(
        email=f"user-{uuid.uuid4()}@example.com",
        hashed_password="hashed",
        role=UserRole.TRADER,
    )
    session.add(user)
    await session.flush()

    account = CreditAccount(
        user_id=user.id,
        total_credits=25,
        available_credits=25,
    )
    session.add(account)
    await session.commit()
    await session.refresh(user)

    return user.id


async def _create_admin_with_account(session) -> uuid.UUID:
    admin = User(
        email=f"admin-{uuid.uuid4()}@example.com",
        hashed_password="hashed",
        role=UserRole.ADMIN,
    )
    session.add(admin)
    await session.flush()

    account = CreditAccount(
        user_id=admin.id,
        total_credits=500,
        available_credits=500,
    )
    session.add(account)
    await session.commit()
    await session.refresh(admin)

    return admin.id


@pytest.mark.asyncio()
async def test_purchase_strategy_access_persists_without_redis(marketplace_env):
    service, SessionLocal = marketplace_env

    async with SessionLocal() as session:
        user_id = await _create_user_with_account(session)

    result = await service.purchase_strategy_access(
        user_id,
        "ai_spot_momentum_strategy",
        subscription_type="permanent",
    )

    assert result["success"] is True

    async with SessionLocal() as session:
        records = await session.execute(
            select(UserStrategyAccess).where(UserStrategyAccess.user_id == user_id)
        )
        entries = records.scalars().all()

    assert len(entries) == 1
    access = entries[0]
    assert access.strategy_id == "ai_spot_momentum_strategy"
    assert access.access_type == StrategyAccessType.WELCOME
    metadata = access.metadata_json or {}
    assert metadata.get("name") == "AI Momentum Trading"
    assert metadata.get("publisher_name") == "CryptoUniverse AI"
    assert metadata.get("credit_cost_monthly") == 0


@pytest.mark.asyncio()
async def test_portfolio_fetch_uses_database_when_redis_missing(marketplace_env):
    service, SessionLocal = marketplace_env

    async with SessionLocal() as session:
        user_id = await _create_user_with_account(session)
        # Ensure access record exists
        session.add(
            UserStrategyAccess(
                user_id=user_id,
                strategy_id="ai_spot_momentum_strategy",
                strategy_type=StrategyType.AI_STRATEGY,
                access_type=StrategyAccessType.WELCOME,
                subscription_type="permanent",
                credits_paid=0,
                is_active=True,
            )
        )
        await session.commit()

    portfolio = await service.get_user_strategy_portfolio(str(user_id))

    assert portfolio.get("success") is True
    strategies = portfolio.get("active_strategies", [])
    assert strategies
    assert any(s.get("strategy_id") == "ai_spot_momentum_strategy" for s in strategies)


@pytest.mark.asyncio()
async def test_admin_portfolio_snapshot_returns_strategies(marketplace_env):
    service, SessionLocal = marketplace_env

    async with SessionLocal() as session:
        admin_id = await _create_admin_with_account(session)

    snapshot = await service.get_admin_portfolio_snapshot(str(admin_id))

    assert snapshot is not None
    assert snapshot.get("success") is True
    assert snapshot.get("total_strategies", 0) > 0
    assert snapshot.get("active_strategies")
