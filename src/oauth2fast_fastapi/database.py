from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .settings import settings

DB_URL = f"postgresql+asyncpg://{settings.auth_db.username}:{settings.auth_db.password.get_secret_value()}@{settings.auth_db.hostname}:{settings.auth_db.port}/{settings.auth_db.name}"
engine = create_async_engine(DB_URL, echo=False)


# Sesion asíncrona
async_session = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)
