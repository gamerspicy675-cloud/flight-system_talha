"""Async SQLAlchemy database configuration and FastAPI dependencies."""

from collections.abc import AsyncGenerator
from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class shared by every SQLAlchemy ORM model."""

    pass


def _async_database_url(url: str) -> str:
    """Convert PostgreSQL/libpq URLs to asyncpg-compatible URLs."""

    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    parts = urlsplit(url)
    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key == "sslmode":
            # Neon URLs commonly use libpq's sslmode; asyncpg uses ssl instead.
            query.append(("ssl", value))
        elif key != "channel_binding":
            # libpq-only setting that asyncpg does not accept.
            query.append((key, value))

    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


@lru_cache
def get_engine() -> AsyncEngine:
    """Create the database engine only when database access is needed."""

    if not settings.DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL or NEON_DATABASE_URL must be set before using database endpoints."
        )

    return create_async_engine(_async_database_url(settings.DATABASE_URL), pool_pre_ping=True)


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create the session factory only when a database route is requested."""

    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield one transactional async session for a request."""

    async with get_session_factory()() as session:
        yield session
