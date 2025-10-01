"""Strategy submission workflow service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from app.api.v1.endpoints.strategies import (
        StrategySubmissionRequest,
        StrategySubmissionUpdate,
    )

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.async_session_manager import DatabaseSessionMixin
from app.core.caching import cache_manager
from app.core.redis import cache_manager as redis_cache_manager
from app.core.logging import LoggerMixin
from app.models.copy_trading import StrategyPublisher
from app.models.strategy_submission import (
    ComplexityLevel,
    PricingModel,
    StrategyStatus,
    StrategySubmission,
    SupportLevel,
)
from app.models.trading import StrategyType, TradingStrategy
from app.models.user import User


@dataclass
class ReviewStats:
    """Aggregated counts for the admin dashboard."""

    total_pending: int
    under_review: int
    approved_today: int
    rejected_today: int
    avg_review_time_hours: int
    my_assigned: int


class StrategySubmissionService(DatabaseSessionMixin, LoggerMixin):
    """Coordinates the end-to-end lifecycle of community strategy submissions."""

    REVIEW_HISTORY_KEY = "review_history"
    REVIEW_STATE_KEY = "review_state"
    PUBLISHED_STRATEGY_KEY = "published_strategy_id"

    CATEGORY_TO_STRATEGY_TYPE = {
        "algorithmic": StrategyType.ALGORITHMIC,
        "momentum": StrategyType.MOMENTUM,
        "mean_reversion": StrategyType.MEAN_REVERSION,
        "arbitrage": StrategyType.ARBITRAGE,
        "scalping": StrategyType.SCALPING,
        "dca": StrategyType.DCA,
    }

    def __init__(self) -> None:
        super().__init__()

    @property
    def logger(self):  # type: ignore[override]
        return super().logger.bind(service="strategy_submission_service")

    # ------------------------------------------------------------------
    # Publisher operations
    # ------------------------------------------------------------------
    async def create_submission(
        self,
        request: "StrategySubmissionRequest",
        user: User,
        db: AsyncSession,
    ) -> StrategySubmission:
        """Persist a new submission for the requesting publisher."""

        submission = StrategySubmission(
            user_id=str(user.id),
            name=request.name,
            description=request.description,
            category=request.category or "algorithmic",
            risk_level=request.risk_level,
            expected_return_min=float(request.expected_return_range[0])
            if request.expected_return_range
            else 0.0,
            expected_return_max=float(request.expected_return_range[1])
            if request.expected_return_range
            else 0.0,
            required_capital=Decimal(str(request.required_capital))
            if request.required_capital is not None
            else Decimal("1000"),
            pricing_model=request.pricing_model,
            price_amount=Decimal(str(request.price_amount))
            if request.price_amount is not None
            else None,
            profit_share_percentage=float(request.profit_share_percentage)
            if request.profit_share_percentage is not None
            else None,
            status=StrategyStatus.SUBMITTED,
            submitted_at=datetime.utcnow(),
            tags=list(request.tags or []),
            target_audience=list(request.target_audience or []),
            complexity_level=request.complexity_level,
            support_level=request.support_level,
        )

        submission.strategy_config = {
            "source_strategy_id": request.strategy_id,
            self.REVIEW_STATE_KEY: StrategyStatus.SUBMITTED.value,
            self.REVIEW_HISTORY_KEY: [
                {
                    "action": "submitted",
                    "reviewer": None,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ],
        }

        db.add(submission)
        await db.commit()
        await db.refresh(submission)

        self.logger.info(
            "strategy_submission_created",
            submission_id=submission.id,
            user_id=str(user.id),
        )

        return submission

    async def list_user_submissions(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> List[StrategySubmission]:
        stmt = (
            select(StrategySubmission)
            .options(joinedload(StrategySubmission.reviewer))
            .where(StrategySubmission.user_id == user_id)
            .order_by(StrategySubmission.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def withdraw_submission(
        self,
        submission_id: str,
        user: User,
        db: AsyncSession,
    ) -> StrategySubmission:
        submission = await self._get_submission_for_user(
            submission_id=submission_id,
            user=user,
            db=db,
        )

        if submission.status in {StrategyStatus.APPROVED, StrategyStatus.PUBLISHED}:
            raise ValueError("Approved or published strategies cannot be withdrawn")

        submission.status = StrategyStatus.WITHDRAWN
        submission.updated_at = datetime.utcnow()
        submission.strategy_config = submission.strategy_config or {}
        submission.strategy_config[self.REVIEW_STATE_KEY] = StrategyStatus.WITHDRAWN.value
        self._append_history_entry(submission, "withdrawn", user.email)

        await db.commit()
        await db.refresh(submission)
        return submission

    async def update_submission(
        self,
        submission_id: str,
        user: User,
        updates: "StrategySubmissionUpdate",
        db: AsyncSession,
    ) -> StrategySubmission:
        submission = await self._get_submission_for_user(
            submission_id=submission_id,
            user=user,
            db=db,
        )

        if submission.status in {
            StrategyStatus.APPROVED,
            StrategyStatus.PUBLISHED,
            StrategyStatus.REJECTED,
        }:
            raise ValueError("Completed submissions cannot be modified")

        payload = updates.model_dump(exclude_unset=True)
        if "name" in payload:
            name_value = payload["name"]
            if name_value is None:
                raise ValueError("Submission name cannot be null")
            if not isinstance(name_value, str):
                raise ValueError("Submission name must be a string")
            submission.name = name_value.strip()
        if "description" in payload:
            description_value = payload["description"]
            if description_value is None:
                raise ValueError("Submission description cannot be null")
            if not isinstance(description_value, str):
                raise ValueError("Submission description must be a string")
            submission.description = description_value.strip()
        if "category" in payload and payload["category"]:
            submission.category = payload["category"]
        if "risk_level" in payload and payload["risk_level"]:
            submission.risk_level = submission.risk_level.__class__(payload["risk_level"])
        if "expected_return_range" in payload:
            min_ret, max_ret = payload["expected_return_range"]
            submission.expected_return_min = float(min_ret)
            submission.expected_return_max = float(max_ret)
        if "required_capital" in payload and payload["required_capital"] is not None:
            submission.required_capital = Decimal(str(payload["required_capital"]))
        if "pricing_model" in payload and payload["pricing_model"]:
            submission.pricing_model = PricingModel(payload["pricing_model"])
        if "price_amount" in payload:
            price_amount = payload["price_amount"]
            submission.price_amount = (
                Decimal(str(price_amount)) if price_amount is not None else None
            )
        if "profit_share_percentage" in payload:
            submission.profit_share_percentage = (
                float(payload["profit_share_percentage"])
                if payload["profit_share_percentage"] is not None
                else None
            )
        if "tags" in payload:
            submission.tags = list(payload["tags"] or [])
        if "target_audience" in payload:
            submission.target_audience = list(payload["target_audience"] or [])
        if "complexity_level" in payload and payload["complexity_level"]:
            submission.complexity_level = ComplexityLevel(payload["complexity_level"])
        if "support_level" in payload and payload["support_level"]:
            submission.support_level = SupportLevel(payload["support_level"])

        submission.updated_at = datetime.utcnow()
        submission.strategy_config = submission.strategy_config or {}
        self._append_history_entry(submission, "updated", user.email)

        await db.commit()
        await db.refresh(submission)
        return submission

    # ------------------------------------------------------------------
    # Admin operations
    # ------------------------------------------------------------------
    async def get_review_stats(
        self, db: AsyncSession, reviewer: Optional[User]
    ) -> ReviewStats:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        total_pending_stmt = select(func.count(StrategySubmission.id)).where(
            StrategySubmission.status.in_([
                StrategyStatus.SUBMITTED,
                StrategyStatus.UNDER_REVIEW,
                StrategyStatus.CHANGES_REQUESTED
            ])
        )
        under_review_stmt = select(func.count(StrategySubmission.id)).where(
            StrategySubmission.status == StrategyStatus.UNDER_REVIEW
        )
        approved_stmt = select(func.count(StrategySubmission.id)).where(
            and_(
                StrategySubmission.reviewed_at >= today_start,
                StrategySubmission.status.in_(
                    [StrategyStatus.APPROVED, StrategyStatus.PUBLISHED]
                ),
            )
        )
        rejected_stmt = select(func.count(StrategySubmission.id)).where(
            and_(
                StrategySubmission.reviewed_at >= today_start,
                StrategySubmission.status == StrategyStatus.REJECTED,
            )
        )

        total_pending = (await db.execute(total_pending_stmt)).scalar_one()
        under_review = (await db.execute(under_review_stmt)).scalar_one()
        approved_today = (await db.execute(approved_stmt)).scalar_one()
        rejected_today = (await db.execute(rejected_stmt)).scalar_one()

        avg_review_time_hours = await self._calculate_average_review_hours(db)

        my_assigned = 0
        if reviewer:
            assigned_stmt = select(func.count(StrategySubmission.id)).where(
                and_(
                    StrategySubmission.reviewer_id == str(reviewer.id),
                    StrategySubmission.status.in_(pending_statuses),
                )
            )
            my_assigned = (await db.execute(assigned_stmt)).scalar_one()

        return ReviewStats(
            total_pending=int(total_pending or 0),
            under_review=int(under_review or 0),
            approved_today=int(approved_today or 0),
            rejected_today=int(rejected_today or 0),
            avg_review_time_hours=avg_review_time_hours,
            my_assigned=int(my_assigned or 0),
        )

    async def get_pending_submissions(
        self,
        db: AsyncSession,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        changes_requested_status = getattr(StrategyStatus, "CHANGES_REQUESTED", None)
        pending_statuses = [StrategyStatus.SUBMITTED, StrategyStatus.UNDER_REVIEW]
        if changes_requested_status:
            pending_statuses.append(changes_requested_status)

        stmt = (
            select(StrategySubmission)
            .options(
                joinedload(StrategySubmission.user),
                joinedload(StrategySubmission.reviewer),
            )
            .where(
                StrategySubmission.status.in_(
                    [
                        StrategyStatus.SUBMITTED,
                        StrategyStatus.UNDER_REVIEW,
                        StrategyStatus.CHANGES_REQUESTED,
                        StrategyStatus.APPROVED,
                        StrategyStatus.REJECTED,
                        StrategyStatus.PUBLISHED,
                    ]
                )
            )
            .order_by(StrategySubmission.submitted_at.desc())
        )

        result = await db.execute(stmt)
        submissions = list(result.scalars().all())

        payload = [self._build_admin_payload(submission) for submission in submissions]

        if status_filter and status_filter != "all":
            payload = [
                item for item in payload if item["status"] == status_filter
            ]

        return payload

    async def assign_submission(
        self,
        submission_id: str,
        reviewer: User,
        db: AsyncSession,
    ) -> StrategySubmission:
        submission = await self._get_submission_by_id(submission_id, db)

        allowed_statuses = {
            StrategyStatus.SUBMITTED,
            StrategyStatus.UNDER_REVIEW,
        }
        changes_requested_status = getattr(
            StrategyStatus, "CHANGES_REQUESTED", None
        )
        if changes_requested_status is not None:
            allowed_statuses.add(changes_requested_status)

        if submission.status not in allowed_statuses:
            status_value = submission.status.value if submission.status else "unknown"
            raise ValueError(
                "Cannot assign submission while status is "
                f"'{status_value}'; only submitted, under_review"
                f"{', changes_requested' if changes_requested_status else ''}"
                " submissions can be reassigned."
            )

        submission.reviewer_id = str(reviewer.id)
        submission.status = StrategyStatus.UNDER_REVIEW
        submission.strategy_config = submission.strategy_config or {}
        submission.strategy_config[self.REVIEW_STATE_KEY] = "under_review"
        self._append_history_entry(submission, "assigned", reviewer.email)
        submission.reviewed_at = None

        await db.commit()
        await db.refresh(submission)
        return submission

    async def review_submission(
        self,
        submission_id: str,
        reviewer: User,
        action: str,
        comment: Optional[str],
        db: AsyncSession,
    ) -> StrategySubmission:
        submission = await self._get_submission_by_id(submission_id, db)
        submission.reviewer_id = str(reviewer.id)
        submission.strategy_config = submission.strategy_config or {}
        now = datetime.utcnow()

        if action == "approve":
            submission.status = StrategyStatus.APPROVED
            submission.reviewed_at = now
            submission.reviewer_feedback = comment
            submission.rejection_reason = None
            submission.strategy_config[self.REVIEW_STATE_KEY] = "approved"
            self._append_history_entry(submission, "approved", reviewer.email, comment)
            await self._promote_submission_to_marketplace(submission, db)
        elif action == "reject":
            submission.status = StrategyStatus.REJECTED
            submission.reviewed_at = now
            submission.rejection_reason = comment or "Strategy rejected"
            submission.reviewer_feedback = None
            submission.strategy_config[self.REVIEW_STATE_KEY] = "rejected"
            self._append_history_entry(submission, "rejected", reviewer.email, comment)
        elif action == "request_changes":
            changes_requested_status = StrategyStatus.CHANGES_REQUESTED
            submission.status = changes_requested_status
            submission.reviewed_at = now
            submission.reviewer_feedback = comment
            submission.strategy_config[self.REVIEW_STATE_KEY] = (
                changes_requested_status.value
            )
            self._append_history_entry(
                submission, "changes_requested", reviewer.email, comment
            )
        else:
            raise ValueError(f"Unsupported review action: {action}")

        await db.commit()
        await db.refresh(submission)
        await self._invalidate_marketplace_cache()
        return submission

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _get_submission_for_user(
        self,
        submission_id: str,
        user: User,
        db: AsyncSession,
    ) -> StrategySubmission:
        stmt = select(StrategySubmission).where(
            and_(
                StrategySubmission.id == submission_id,
                StrategySubmission.user_id == str(user.id),
            )
        )
        result = await db.execute(stmt)
        submission = result.scalar_one_or_none()
        if not submission:
            raise ValueError("Strategy submission not found")
        return submission

    async def _get_submission_by_id(
        self, submission_id: str, db: AsyncSession
    ) -> StrategySubmission:
        stmt = select(StrategySubmission).options(joinedload(StrategySubmission.user)).where(
            StrategySubmission.id == submission_id
        )
        result = await db.execute(stmt)
        submission = result.scalar_one_or_none()
        if not submission:
            raise ValueError("Strategy submission not found")
        return submission

    async def _promote_submission_to_marketplace(
        self, submission: StrategySubmission, db: AsyncSession
    ) -> None:
        user_uuid = uuid.UUID(submission.user_id)
        user = await db.get(User, user_uuid)
        if not user:
            raise ValueError("Submission owner no longer exists")

        publisher_stmt = select(StrategyPublisher).where(
            StrategyPublisher.user_id == user_uuid
        )
        publisher_result = await db.execute(publisher_stmt)
        publisher = publisher_result.scalar_one_or_none()
        new_publisher = False
        if not publisher:
            display_name = "Publisher"
            if user:
                full_name_attr = getattr(user, "full_name", None)
                if callable(full_name_attr):
                    full_name_value = full_name_attr()
                else:
                    full_name_value = full_name_attr
                if full_name_value:
                    display_name = full_name_value
                elif user.email:
                    display_name = user.email.split("@")[0]
            publisher = StrategyPublisher(
                user_id=user_uuid,
                display_name=display_name,
                verified=True,
                total_followers=0,
                total_strategies=0,
            )
            db.add(publisher)
            new_publisher = True
        else:
            publisher.verified = True

        strategy = await self._upsert_trading_strategy(submission, user_uuid, db)

        submission.status = StrategyStatus.PUBLISHED
        submission.published_at = datetime.utcnow()
        submission.strategy_config[self.PUBLISHED_STRATEGY_KEY] = str(strategy.id)
        submission.strategy_config[self.REVIEW_STATE_KEY] = "published"

        if new_publisher:
            publisher.total_strategies = 1
        else:
            publisher.total_strategies = (publisher.total_strategies or 0) + 1

    async def _upsert_trading_strategy(
        self,
        submission: StrategySubmission,
        user_uuid: uuid.UUID,
        db: AsyncSession,
    ) -> TradingStrategy:
        existing_id = submission.strategy_config.get(self.PUBLISHED_STRATEGY_KEY)
        strategy: Optional[TradingStrategy] = None
        if existing_id:
            try:
                strategy = await db.get(TradingStrategy, uuid.UUID(existing_id))
            except ValueError:
                strategy = None

        if not strategy:
            strategy_stmt = select(TradingStrategy).where(
                and_(
                    TradingStrategy.user_id == user_uuid,
                    TradingStrategy.name == submission.name,
                )
            )
            strategy_result = await db.execute(strategy_stmt)
            strategy = strategy_result.scalar_one_or_none()

        is_new = strategy is None

        if not strategy:
            strategy = TradingStrategy(
                user_id=user_uuid,
                name=submission.name,
                description=submission.description,
                strategy_type=self.CATEGORY_TO_STRATEGY_TYPE.get(
                    submission.category, StrategyType.ALGORITHMIC
                ),
                parameters=self._extract_parameters(submission),
                risk_parameters=self._extract_risk_parameters(submission),
                entry_conditions=self._extract_entry_conditions(submission),
                exit_conditions=self._extract_exit_conditions(submission),
                target_symbols=self._extract_target_symbols(submission),
                target_exchanges=self._extract_target_exchanges(submission),
                timeframe=self._extract_timeframe(submission),
                max_positions=self._extract_max_positions(submission),
                max_risk_per_trade=self._calculate_max_risk(submission),
                is_active=True,
                is_simulation=True,
            )
            db.add(strategy)
        else:
            strategy.description = submission.description
            strategy.strategy_type = self.CATEGORY_TO_STRATEGY_TYPE.get(
                submission.category, StrategyType.ALGORITHMIC
            )
            strategy.parameters = self._extract_parameters(submission)
            strategy.risk_parameters = self._extract_risk_parameters(submission)
            strategy.entry_conditions = self._extract_entry_conditions(submission)
            strategy.exit_conditions = self._extract_exit_conditions(submission)
            strategy.target_symbols = self._extract_target_symbols(submission)
            strategy.target_exchanges = self._extract_target_exchanges(submission)
            strategy.timeframe = self._extract_timeframe(submission)
            strategy.max_positions = self._extract_max_positions(submission)
            strategy.max_risk_per_trade = self._calculate_max_risk(submission)
            strategy.is_active = True

        backtest = submission.backtest_results or {}
        strategy.total_trades = int(backtest.get("total_trades", 0) or 0)
        strategy.winning_trades = self._calculate_winning_trades(backtest)
        strategy.total_pnl = Decimal(
            str(backtest.get("total_return", 0.0) or 0.0)
        )
        strategy.max_drawdown = Decimal(
            str(backtest.get("max_drawdown", 0.0) or 0.0)
        )
        strategy.sharpe_ratio = Decimal(
            str(backtest.get("sharpe_ratio", 0.0) or 0.0)
        )

        if is_new:
            self.logger.info(
                "community_strategy_published",
                submission_id=submission.id,
                strategy_id=str(strategy.id),
            )
        return strategy

    async def _invalidate_marketplace_cache(self) -> None:
        """Clear cached marketplace responses after publishing updates."""

        try:
            await cache_manager.delete("strategies:marketplace")
        except Exception as exc:  # pragma: no cover - best-effort cleanup
            self.logger.warning(
                "legacy_marketplace_cache_invalidation_failed",
                error=str(exc),
            )

        try:
            redis_client = await redis_cache_manager.redis.get_client()
        except Exception as exc:  # pragma: no cover - redis unavailable
            self.logger.warning(
                "marketplace_cache_invalidation_unavailable",
                error=str(exc),
            )
            return

        if redis_client is None:
            return

        pattern = "marketplace:*"
        batch: List[str] = []

        try:
            async for key in redis_client.scan_iter(match=pattern, count=100):
                key_str = (
                    key.decode("utf-8")
                    if isinstance(key, (bytes, bytearray))
                    else str(key)
                )
                batch.append(key_str)
                if len(batch) >= 100:
                    await redis_client.delete(*batch)
                    batch.clear()

            if batch:
                await redis_client.delete(*batch)
        except Exception as exc:  # pragma: no cover - best-effort cleanup
            self.logger.warning(
                "marketplace_cache_prefix_purge_failed",
                pattern=pattern,
                error=str(exc),
            )

    async def _calculate_average_review_hours(self, db: AsyncSession) -> int:
        stmt = select(
            StrategySubmission.submitted_at, StrategySubmission.reviewed_at
        ).where(StrategySubmission.reviewed_at.is_not(None))
        result = await db.execute(stmt)
        durations = []
        for submitted_at, reviewed_at in result.all():
            if submitted_at and reviewed_at:
                durations.append((reviewed_at - submitted_at).total_seconds())

        if not durations:
            return 0

        avg_seconds = sum(durations) / len(durations)
        return int(avg_seconds // 3600) or 0

    def _build_admin_payload(self, submission: StrategySubmission) -> Dict[str, Any]:
        user = submission.user
        reviewer = submission.reviewer
        review_state = (submission.strategy_config or {}).get(
            self.REVIEW_STATE_KEY, submission.status.value
        )
        status = self._map_admin_status(submission.status, review_state)

        backtest = submission.backtest_results or {}
        validation = submission.validation_results or {}
        review_history = list(
            (submission.strategy_config or {}).get(self.REVIEW_HISTORY_KEY, [])
        )

        if user:
            full_name_attr = getattr(user, "full_name", None)
            if callable(full_name_attr):
                publisher_name = full_name_attr()
            else:
                publisher_name = full_name_attr
            if not publisher_name and user.email:
                publisher_name = user.email.split("@")[0]
        else:
            publisher_name = None

        return {
            "id": submission.id,
            "name": submission.name,
            "description": submission.description,
            "category": submission.category,
            "publisher_id": str(user.id) if user else None,
            "publisher_name": publisher_name or (user.email.split("@")[0] if user and user.email else "Unknown"),
            "publisher_email": user.email if user else None,
            "risk_level": submission.risk_level.value if submission.risk_level else "medium",
            "complexity_level": submission.complexity_level.value
            if submission.complexity_level
            else "intermediate",
            "expected_return_range": [
                float(submission.expected_return_min or 0.0),
                float(submission.expected_return_max or 0.0),
            ],
            "required_capital": float(submission.required_capital or 0.0),
            "max_positions": self._extract_max_positions(submission),
            "trading_pairs": (submission.strategy_config or {}).get(
                "trading_pairs", ["BTC/USDT"]
            ),
            "timeframes": (submission.strategy_config or {}).get(
                "timeframes", [self._extract_timeframe(submission)]
            ),
            "tags": submission.tags or [],
            "pricing_model": submission.pricing_model.value
            if submission.pricing_model
            else PricingModel.FREE.value,
            "price_amount": float(submission.price_amount or 0.0)
            if submission.price_amount is not None
            else None,
            "profit_share_percentage": submission.profit_share_percentage,
            "status": status,
            "submitted_at": submission.submitted_at.isoformat()
            if submission.submitted_at
            else None,
            "assigned_reviewer": reviewer.email if reviewer else None,
            "review_started_at": (submission.strategy_config or {}).get(
                "review_started_at"
            ),
            "review_due_date": (submission.strategy_config or {}).get(
                "review_due_date"
            ),
            "backtest_results": {
                "total_return": float(backtest.get("total_return", 0.0) or 0.0),
                "sharpe_ratio": float(backtest.get("sharpe_ratio", 0.0) or 0.0),
                "max_drawdown": float(backtest.get("max_drawdown", 0.0) or 0.0),
                "win_rate": float(backtest.get("win_rate", 0.0) or 0.0),
                "total_trades": int(backtest.get("total_trades", 0) or 0),
                "profit_factor": float(backtest.get("profit_factor", 0.0) or 0.0),
                "volatility": float(backtest.get("volatility", 0.0) or 0.0),
                "period_days": int(backtest.get("period_days", 0) or 0),
            },
            "validation_results": {
                "is_valid": bool(validation.get("is_valid", False)),
                "security_score": int(validation.get("security_score", 0) or 0),
                "performance_score": int(validation.get("performance_score", 0) or 0),
                "code_quality_score": int(validation.get("code_quality_score", 0) or 0),
                "overall_score": int(validation.get("overall_score", 0) or 0),
                "issues": validation.get("issues", []),
            },
            "review_history": review_history,
            "documentation": (submission.strategy_config or {}).get(
                "documentation",
                {
                    "readme": submission.description or "",
                    "changelog": None,
                    "examples": [],
                    "api_reference": None,
                },
            ),
        }

    def _map_admin_status(
        self, status: StrategyStatus, review_state: Optional[str]
    ) -> str:
        if review_state == "changes_requested":
            return "changes_requested"
        if review_state == "rejected":
            return "rejected"
        if review_state == "approved" or review_state == "published":
            return "approved"
        if status == StrategyStatus.REJECTED:
            return "rejected"
        if status == StrategyStatus.APPROVED:
            return "approved"
        if status == StrategyStatus.PUBLISHED:
            return "approved"
        if status == StrategyStatus.UNDER_REVIEW:
            return "under_review"
        return "submitted"

    def _append_history_entry(
        self,
        submission: StrategySubmission,
        action: str,
        reviewer: Optional[str],
        comment: Optional[str] = None,
    ) -> None:
        submission.strategy_config = submission.strategy_config or {}
        history: List[Dict[str, Any]] = list(
            submission.strategy_config.get(self.REVIEW_HISTORY_KEY, [])
        )
        history.append(
            {
                "action": action,
                "reviewer": reviewer,
                "timestamp": datetime.utcnow().isoformat(),
                "comment": comment,
            }
        )
        submission.strategy_config[self.REVIEW_HISTORY_KEY] = history

    def _extract_parameters(self, submission: StrategySubmission) -> Dict[str, Any]:
        config = submission.strategy_config or {}
        parameters = config.get("parameters")
        if isinstance(parameters, dict) and parameters:
            return parameters
        return {
            "source": "community_submission",
            "target_audience": submission.target_audience or [],
            "tags": submission.tags or [],
        }

    def _extract_risk_parameters(
        self, submission: StrategySubmission
    ) -> Dict[str, Any]:
        config = submission.strategy_config or {}
        risk_parameters = config.get("risk_parameters")
        if isinstance(risk_parameters, dict) and risk_parameters:
            return risk_parameters
        return {
            "risk_level": submission.risk_level.value if submission.risk_level else "medium",
            "required_capital": float(submission.required_capital or 0.0),
            "max_drawdown": float(
                (submission.backtest_results or {}).get("max_drawdown", 0.0)
            ),
        }

    def _extract_entry_conditions(
        self, submission: StrategySubmission
    ) -> List[Dict[str, Any]]:
        config = submission.strategy_config or {}
        entry_conditions = config.get("entry_conditions")
        if isinstance(entry_conditions, list) and entry_conditions:
            return entry_conditions
        return [
            {
                "type": "signal",
                "condition": "entry_rule_defined_in_submission",
            }
        ]

    def _extract_exit_conditions(
        self, submission: StrategySubmission
    ) -> List[Dict[str, Any]]:
        config = submission.strategy_config or {}
        exit_conditions = config.get("exit_conditions")
        if isinstance(exit_conditions, list) and exit_conditions:
            return exit_conditions
        return [
            {
                "type": "signal",
                "condition": "exit_rule_defined_in_submission",
            }
        ]

    def _extract_target_symbols(self, submission: StrategySubmission) -> List[str]:
        config = submission.strategy_config or {}
        target_symbols = config.get("target_symbols")
        if isinstance(target_symbols, list) and target_symbols:
            return target_symbols
        return ["BTCUSDT"]

    def _extract_target_exchanges(self, submission: StrategySubmission) -> List[str]:
        config = submission.strategy_config or {}
        target_exchanges = config.get("target_exchanges")
        if isinstance(target_exchanges, list) and target_exchanges:
            return target_exchanges
        return ["binance"]

    def _extract_timeframe(self, submission: StrategySubmission) -> str:
        config = submission.strategy_config or {}
        timeframe = config.get("timeframe")
        if isinstance(timeframe, str) and timeframe:
            return timeframe
        return "1h"

    def _extract_max_positions(self, submission: StrategySubmission) -> int:
        config = submission.strategy_config or {}
        max_positions = config.get("max_positions")
        if isinstance(max_positions, int) and max_positions > 0:
            return max_positions
        return 3

    def _calculate_max_risk(self, submission: StrategySubmission) -> Decimal:
        risk_map = {
            "low": Decimal("1.0"),
            "medium": Decimal("2.0"),
            "high": Decimal("3.5"),
        }
        risk_level = submission.risk_level.value if submission.risk_level else "medium"
        return risk_map.get(risk_level, Decimal("2.0"))

    def _calculate_winning_trades(self, backtest: Dict[str, Any]) -> int:
        total_trades = int(backtest.get("total_trades", 0) or 0)
        win_rate = backtest.get("win_rate", 0.0) or 0.0
        if win_rate > 1:
            win_rate = win_rate / 100.0
        return int(total_trades * win_rate)


strategy_submission_service = StrategySubmissionService()

