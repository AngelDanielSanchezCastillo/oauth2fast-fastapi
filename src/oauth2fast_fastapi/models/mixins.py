from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlmodel import BigInteger, Field


class IdMixin:
    """Mixin para proveer clave primaria autoincremental tipo BigInteger."""

    id: int | None = Field(default=None, primary_key=True, index=True, sa_type=BigInteger)


class TimestampMixin:
    """Mixin reutilizable para marcas de tiempo en UTC."""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"onupdate": func.now()},
    )


class AuditMixin:
    """Mixin para rastrear el usuario que crea y actualiza un registro."""

    created_by: int | None = Field(
        default=None,
        description="ID of the user who created this record.",
        sa_type=BigInteger,
    )
    updated_by: int | None = Field(
        default=None,
        description="ID of the user who last updated this record.",
        sa_type=BigInteger,
    )


# class Example(TimestampMixin, SQLModel, table=True):
#    """Ejemplo de modelo con timestamps automáticos."""
#    id: int | None = Field(default=None, primary_key=True)
#    name: str


# Opcional: asegurar que updated_at se actualice también del lado de Python
# @event.listens_for(Example, "before_update", propagate=True)
# def receive_before_update(mapper, connection, target):
#    target.updated_at = datetime.now(timezone.utc)
