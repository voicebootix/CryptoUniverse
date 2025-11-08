"""Create core schema and seed demo data."""

from __future__ import annotations

from alembic import op
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Base  # noqa: F401 ensures all models are registered
from app.db.seeds import ADMIN_USER_ID, DEFAULT_TENANT_ID, seed_core_data

revision = "20240930_seed_core_data"
down_revision = None
branch_labels = ("seed",)
depends_on = None


def upgrade() -> None:
    """Create tables defined in SQLAlchemy models and seed demo data."""
    bind = op.get_bind()

    # Create tables if they do not exist. `checkfirst=True` ensures idempotency.
    Base.metadata.create_all(bind=bind, checkfirst=True)

    session = Session(bind=bind)
    try:
        seed_core_data(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def downgrade() -> None:
    """Remove seed data without modifying the schema."""
    bind = op.get_bind()
    session = Session(bind=bind)
    try:
        session.execute(
            text("DELETE FROM users WHERE id = :admin_id"),
            {"admin_id": str(ADMIN_USER_ID)},
        )
        session.execute(
            text("DELETE FROM tenant_settings WHERE tenant_id = :tenant_id"),
            {"tenant_id": str(DEFAULT_TENANT_ID)},
        )
        session.execute(
            text("DELETE FROM tenants WHERE id = :tenant_id"),
            {"tenant_id": str(DEFAULT_TENANT_ID)},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
