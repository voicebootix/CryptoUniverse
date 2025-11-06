"""Database seed fixtures for local development and automated tests."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tenant import Tenant, TenantSettings, TenantStatus, TenantType
from app.models.user import User, UserRole, UserStatus

ADMIN_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000101")
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD_HASH = "$2b$12$opH8RUC1EsGbDHH.4ENAOOckmPzEZxVc3BfXM4nwceYOGGbyTMko2"
DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _ensure_tenant(session: Session) -> Tenant:
    tenant: Tenant | None = session.execute(
        select(Tenant).where(Tenant.id == DEFAULT_TENANT_ID)
    ).scalar_one_or_none()

    if tenant is None:
        tenant = Tenant(
            id=DEFAULT_TENANT_ID,
            name="CryptoUniverse Demo",
            slug="cryptouniverse-demo",
            description="Demo tenant for local development and automated tests.",
            tenant_type=TenantType.ENTERPRISE,
            status=TenantStatus.ACTIVE,
            contact_email=ADMIN_EMAIL,
            features_enabled=[
                "opportunity_discovery",
                "portfolio_management",
                "ai_chat",
            ],
            custom_features={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(tenant)

        settings = TenantSettings(
            tenant=tenant,
            timezone="UTC",
            default_currency="USD",
            default_risk_profile="balanced",
            allowed_exchanges=["demo-exchange"],
            custom_domain=None,
        )
        session.add(settings)
    else:
        tenant.status = TenantStatus.ACTIVE
        tenant.features_enabled = _merge_feature_list(
            tenant.features_enabled or [],
            ["opportunity_discovery", "portfolio_management", "ai_chat"],
        )

    return tenant


def _merge_feature_list(existing: Sequence[str], required: Sequence[str]) -> list[str]:
    merged = list(dict.fromkeys([*(existing or []), *required]))
    return merged


def _ensure_admin_user(session: Session, tenant: Tenant | None) -> None:
    user: User | None = session.execute(
        select(User).where(User.id == ADMIN_USER_ID)
    ).scalar_one_or_none()

    if user is None:
        user = User(
            id=ADMIN_USER_ID,
            email=ADMIN_EMAIL,
            hashed_password=ADMIN_PASSWORD_HASH,
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            is_active=True,
            is_verified=True,
            tenant_id=tenant.id if tenant else None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            simulation_mode=True,
            simulation_balance=100000,
        )
        session.add(user)
    else:
        user.email = ADMIN_EMAIL
        user.hashed_password = ADMIN_PASSWORD_HASH
        user.role = UserRole.ADMIN
        user.status = UserStatus.ACTIVE
        user.is_active = True
        user.is_verified = True
        if tenant:
            user.tenant_id = tenant.id


def seed_core_data(session: Session) -> None:
    """Ensure essential demo records are available."""

    tenant = _ensure_tenant(session)
    _ensure_admin_user(session, tenant)
    session.flush()
