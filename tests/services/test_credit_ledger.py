"""Credit ledger integration tests for credit accounting flows."""

import os
import sys
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

sys.path.append(str(Path(__file__).resolve().parents[2]))


if not hasattr(SQLiteTypeCompiler, "visit_UUID"):
    def _visit_uuid(_, __, **_kw):  # pragma: no cover - SQLite shim
        return "CHAR(36)"

    SQLiteTypeCompiler.visit_UUID = _visit_uuid  # type: ignore[attr-defined]

from app.models.credit import (  # noqa: E402
    CreditAccount,
    CreditStatus,
    CreditTransaction,
    CreditTransactionType,
)
from app.services.credit_ledger import (  # noqa: E402
    InsufficientCreditsError,
    credit_ledger,
)


@pytest_asyncio.fixture()
async def ledger_session(tmp_path):
    """Provide a fresh SQLite database session for each test case."""

    db_path = tmp_path / "credit_ledger.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)

    async with engine.begin() as conn:
        await conn.execute(sa.text("PRAGMA foreign_keys=OFF"))
        await conn.execute(sa.text("CREATE TABLE IF NOT EXISTS users (id CHAR(36) PRIMARY KEY)"))
        await conn.execute(sa.text("CREATE TABLE IF NOT EXISTS credit_packs (id CHAR(36) PRIMARY KEY)"))
        await conn.execute(sa.text("CREATE TABLE IF NOT EXISTS trades (id CHAR(36) PRIMARY KEY)"))
        await conn.execute(sa.text("CREATE TABLE IF NOT EXISTS billing_history (id CHAR(36) PRIMARY KEY)"))
        await conn.run_sync(
            lambda connection: CreditAccount.__table__.create(connection, checkfirst=True)
        )
        await conn.run_sync(
            lambda connection: CreditTransaction.__table__.create(connection, checkfirst=True)
        )

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with SessionLocal() as session:
            yield session
            await session.rollback()
    finally:
        await engine.dispose()


async def _create_user(session) -> uuid.UUID:
    user_id = uuid.uuid4()
    await session.execute(
        sa.text("INSERT INTO users (id) VALUES (:id)"),
        {"id": str(user_id)},
    )
    await session.flush()
    return user_id


@pytest.mark.asyncio()
async def test_add_credits_updates_account_and_logs_transaction(ledger_session):
    user_id = await _create_user(ledger_session)

    account = await credit_ledger.get_account(
        ledger_session,
        user_id,
        create_if_missing=True,
    )

    tx = await credit_ledger.add_credits(
        ledger_session,
        account,
        credits=250,
        transaction_type=CreditTransactionType.PURCHASE,
        description="Starter pack purchase",
        source="test-suite",
        usd_value=Decimal("250"),
        metadata={"order_id": "ORD-001"},
    )

    await ledger_session.commit()
    await ledger_session.refresh(account)

    assert account.available_credits == 250
    assert account.total_credits == 250
    assert account.total_purchased_credits == 250
    assert tx.status == CreditStatus.ACTIVE
    assert tx.balance_before == 0
    assert tx.balance_after == 250


@pytest.mark.asyncio()
async def test_consume_credits_deducts_balance_and_stores_profit_context(ledger_session):
    user_id = await _create_user(ledger_session)
    account = await credit_ledger.get_account(
        ledger_session,
        user_id,
        create_if_missing=True,
    )

    await credit_ledger.add_credits(
        ledger_session,
        account,
        credits=300,
        transaction_type=CreditTransactionType.PURCHASE,
        description="Initial funding",
        source="seed",
    )

    usage = await credit_ledger.consume_credits(
        ledger_session,
        account,
        credits=75,
        description="Live trade commission",
        source="trade",
        trade_id=uuid.uuid4(),
        profit_amount=Decimal("300"),
    )

    await ledger_session.commit()
    await ledger_session.refresh(account)

    assert account.available_credits == 225
    assert account.used_credits == 75
    assert account.total_used_credits == 75
    assert usage.amount == -75
    assert usage.profit_amount_usd == Decimal("300")

    transactions = await ledger_session.execute(
        select(CreditTransaction).where(CreditTransaction.account_id == account.id)
    )
    recorded = transactions.scalars().all()
    assert len(recorded) == 2
    assert {tx.transaction_type for tx in recorded} == {
        CreditTransactionType.PURCHASE,
        CreditTransactionType.USAGE,
    }


@pytest.mark.asyncio()
async def test_consume_credits_requires_sufficient_balance(ledger_session):
    user_id = await _create_user(ledger_session)
    account = await credit_ledger.get_account(
        ledger_session,
        user_id,
        create_if_missing=True,
    )

    await credit_ledger.add_credits(
        ledger_session,
        account,
        credits=20,
        transaction_type=CreditTransactionType.BONUS,
        description="Referral bonus",
        source="referral",
    )

    await ledger_session.commit()

    with pytest.raises(InsufficientCreditsError):
        await credit_ledger.consume_credits(
            ledger_session,
            account,
            credits=25,
            description="Attempt over balance",
            source="chat",
        )


@pytest.mark.asyncio()
async def test_refund_restores_balances_and_usage_counters(ledger_session):
    user_id = await _create_user(ledger_session)
    account = await credit_ledger.get_account(
        ledger_session,
        user_id,
        create_if_missing=True,
    )

    await credit_ledger.add_credits(
        ledger_session,
        account,
        credits=120,
        transaction_type=CreditTransactionType.PURCHASE,
        description="Primary load",
        source="wallet",
    )

    usage = await credit_ledger.consume_credits(
        ledger_session,
        account,
        credits=60,
        description="Signal execution",
        source="signals",
    )

    refund = await credit_ledger.refund_credits(
        ledger_session,
        account,
        credits=60,
        description="Signal cancelled",
        source="chat_refund",
        reference_transaction_id=usage.id,
    )

    await ledger_session.commit()
    await ledger_session.refresh(account)

    assert account.available_credits == 120
    assert account.used_credits == 0
    assert account.total_used_credits == 0
    assert refund.amount == 60
    assert refund.meta_data.get("refund_for") == str(usage.id)
