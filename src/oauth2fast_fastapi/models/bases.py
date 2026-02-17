from sqlmodel import MetaData, SQLModel

from .mixins import TimestampMixin

metadata = MetaData()


class BaseModel(TimestampMixin, SQLModel):
    __abstract__ = True
    metadata = metadata
