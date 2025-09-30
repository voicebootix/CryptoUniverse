"""Centralized credit ledger management."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Union

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credit import (
    CreditAccount,
    CreditStatus,
    CreditTransaction,
    CreditTransactionType,
)


class CreditLedgerError(Exception):
    """Base exception for credit ledger operations."""


class InsufficientCreditsError(CreditLedgerError):
    """Raised when a debit exceeds the available credit balance."""


def _coerce_decimal(value: Optional[Union[Decimal, float, str]]) -> Optional[Decimal]:
    """Convert numeric input to Decimal while preserving None."""

    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    try:
        return Decimal(str(value))
    except Exception as exc:  # pragma: no cover - defensive programming
        raise ValueError(f"Unable to convert value '{value}' to Decimal") from exc


class CreditLedger:
    """Enterprise-grade credit ledger with consistent accounting rules."""

    def __init__(self) -> None:
        self.logger = structlog.get_logger(__name__)

    @staticmethod
    def _normalize_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not metadata:
            return {}
        return {str(key): value for key, value in metadata.items() if value is not None}

    async def get_account(
        self,
        db: AsyncSession,
        user_id: Union[str, uuid.UUID],
        *,
        for_update: bool = False,
        create_if_missing: bool = False,
        initial_credits: int = 0,
    ) -> Optional[CreditAccount]:
        """Fetch (and optionally create) a credit account."""

        stmt = select(CreditAccount).where(CreditAccount.user_id == user_id)
        if for_update:
            bind = db.get_bind()
            dialect_name = ""
            if bind is not None:
                # AsyncEngine exposes dialect directly; AsyncConnection stores it on .dialect
                dialect = getattr(bind, "dialect", None)
                if dialect is None and hasattr(bind, "sync_engine"):
                    dialect = getattr(bind.sync_engine, "dialect", None)
                if dialect is not None:
                    dialect_name = getattr(dialect, "name", "")

            if dialect_name and dialect_name.lower() != "sqlite":
                stmt = stmt.with_for_update()

        result = await db.execute(stmt)
        account = result.scalar_one_or_none()

        if account or not create_if_missing:
            return account

        account = CreditAccount(user_id=user_id)
        db.add(account)
        await db.flush()

        if initial_credits > 0:
            await self.add_credits(
                db,
                account,
                credits=initial_credits,
                transaction_type=CreditTransactionType.BONUS,
                description="Initial account credits",
                source="system",
                track_lifetime=False,
            )
            await db.flush()

        return account

    async def add_credits(
        self,
        db: AsyncSession,
        account: CreditAccount,
        *,
        credits: int,
        transaction_type: CreditTransactionType,
        description: str,
        source: str,
        provider: Optional[str] = None,
        reference_id: Optional[str] = None,
        usd_value: Optional[Union[Decimal, float, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        track_lifetime: bool = True,
    ) -> CreditTransaction:
        """Increase available credits and record the transaction."""

        if credits <= 0:
            raise ValueError("Credits to add must be positive")

        timestamp = datetime.utcnow()
        balance_before, balance_after = account.register_credit_increase(
            credits,
            track_lifetime=track_lifetime,
            timestamp=timestamp,
        )

        transaction = CreditTransaction(
            account_id=account.id,
            amount=credits,
            transaction_type=transaction_type,
            description=description,
            balance_before=balance_before,
            balance_after=balance_after,
            source=source,
            provider=provider,
            reference_id=reference_id,
            usd_value=_coerce_decimal(usd_value),
            meta_data=self._normalize_metadata(metadata),
            status=CreditStatus.ACTIVE,
            created_at=timestamp,
            processed_at=timestamp,
        )

        db.add(transaction)
        await db.flush()

        self.logger.debug(
            "Credits added",
            account_id=str(account.id),
            credits=credits,
            transaction_type=transaction_type.value,
            source=source,
        )

        return transaction

    async def consume_credits(
        self,
        db: AsyncSession,
        account: CreditAccount,
        *,
        credits: int,
        description: str,
        source: str,
        transaction_type: CreditTransactionType = CreditTransactionType.USAGE,
        metadata: Optional[Dict[str, Any]] = None,
        trade_id: Optional[uuid.UUID] = None,
        profit_amount: Optional[Union[Decimal, float, str]] = None,
        track_usage: bool = True,
    ) -> CreditTransaction:
        """Deduct credits and record the usage transaction."""

        if credits <= 0:
            raise ValueError("Credits to deduct must be positive")

        available_balance = int(account.available_credits or 0)
        if credits > available_balance:
            raise InsufficientCreditsError(
                f"Insufficient credits: required={credits}, available={available_balance}"
            )

        timestamp = datetime.utcnow()
        balance_before, balance_after = account.register_credit_usage(
            credits,
            track_usage=track_usage,
            timestamp=timestamp,
        )

        transaction = CreditTransaction(
            account_id=account.id,
            amount=-credits,
            transaction_type=transaction_type,
            description=description,
            balance_before=balance_before,
            balance_after=balance_after,
            source=source,
            trade_id=trade_id,
            profit_amount_usd=_coerce_decimal(profit_amount),
            meta_data=self._normalize_metadata(metadata),
            status=CreditStatus.ACTIVE,
            created_at=timestamp,
            processed_at=timestamp,
        )

        db.add(transaction)
        await db.flush()

        self.logger.debug(
            "Credits consumed",
            account_id=str(account.id),
            credits=credits,
            transaction_type=transaction_type.value,
            source=source,
        )

        return transaction

    async def refund_credits(
        self,
        db: AsyncSession,
        account: CreditAccount,
        *,
        credits: int,
        description: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
        reference_transaction_id: Optional[uuid.UUID] = None,
    ) -> CreditTransaction:
        """Refund credits that were previously consumed."""

        if credits <= 0:
            raise ValueError("Credits to refund must be positive")

        timestamp = datetime.utcnow()
        balance_before, balance_after = account.reverse_credit_usage(
            credits,
            adjust_usage_totals=True,
            timestamp=timestamp,
        )

        refund_metadata = self._normalize_metadata(metadata)
        if reference_transaction_id:
            refund_metadata.setdefault("refund_for", str(reference_transaction_id))

        transaction = CreditTransaction(
            account_id=account.id,
            amount=credits,
            transaction_type=CreditTransactionType.REFUND,
            description=description,
            balance_before=balance_before,
            balance_after=balance_after,
            source=source,
            meta_data=refund_metadata,
            status=CreditStatus.ACTIVE,
            created_at=timestamp,
            processed_at=timestamp,
        )

        db.add(transaction)
        await db.flush()

        self.logger.debug(
            "Credits refunded",
            account_id=str(account.id),
            credits=credits,
            source=source,
        )

        return transaction


credit_ledger = CreditLedger()
