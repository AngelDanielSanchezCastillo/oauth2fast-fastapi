from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlmodel import Column


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


# class Example(TimestampMixin, SQLModel, table=True):
#    """Ejemplo de modelo con timestamps automáticos."""
#    id: int | None = Field(default=None, primary_key=True)
#    name: str


# Opcional: asegurar que updated_at se actualice también del lado de Python
# @event.listens_for(Example, "before_update", propagate=True)
# def receive_before_update(mapper, connection, target):
#    target.updated_at = datetime.now(timezone.utc)
