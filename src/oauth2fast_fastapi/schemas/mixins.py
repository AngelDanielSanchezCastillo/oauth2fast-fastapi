from datetime import datetime

from sqlmodel import SQLModel


class TimestampMixin(SQLModel):
    created_at: datetime
    updated_at: datetime
