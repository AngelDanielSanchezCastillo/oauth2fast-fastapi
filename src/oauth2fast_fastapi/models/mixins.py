from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlmodel import BigInteger, Column, Field


class IdMixin:
    """Mixin para proveer clave primaria autoincremental tipo BigInteger."""

    id: int = Field(
        default=None, sa_column=Column(BigInteger, index=True, primary_key=True)
    )


class TimestampMixin:
    """Mixin reutilizable para marcas de tiempo en UTC."""

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=func.now(),
    )


class AuditMixin:
    """Mixin para rastrear el usuario que crea y actualiza un registro."""

    created_by: int | None = Field(
        default=None,
        description="ID of the user who created this record.",
        sa_column=Column(BigInteger),
    )
    updated_by: int | None = Field(
        default=None,
        description="ID of the user who last updated this record.",
        sa_column=Column(BigInteger),
    )


# class Example(TimestampMixin, SQLModel, table=True):
#    """Ejemplo de modelo con timestamps automáticos."""
#    id: int | None = Field(default=None, primary_key=True)
#    name: str


# Opcional: asegurar que updated_at se actualice también del lado de Python
# @event.listens_for(Example, "before_update", propagate=True)
# def receive_before_update(mapper, connection, target):
#    target.updated_at = datetime.now(timezone.utc)
