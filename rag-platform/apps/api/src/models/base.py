from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Declarative base for all models.

    The tables themselves are defined in src/db/schema/*.sql, which also
    holds what the ORM doesn't express well (triggers, partial indexes,
    pgvector). These models map onto those tables;
    tests/db/test_models.py checks they stay in sync.
    """


class Timestamped:
    """created_at / updated_at, both set by the database."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    # Kept current by the set_updated_at() trigger; refreshed after updates.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now(),
    )
