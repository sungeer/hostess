import os
from functools import lru_cache
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from viper import settings


def _db_url() -> str:
    return (
        f"mysql+asyncmy://{settings.database_username}:"
        f"{settings.database_password}@{settings.database_host}/"
        f"{settings.database_name}?charset=utf8mb4"
    )


@lru_cache
def get_async_engine(pid: int) -> AsyncEngine:
    return create_async_engine(
        _db_url(),
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
    )


@asynccontextmanager
async def get_async_conn_raw():
    """
    借一个“原生 asyncmy 连接”（DBAPI connection），由 SQLAlchemy 负责池化
    用法：
        async with get_async_conn_raw() as conn:
            async with conn.cursor(...) as cur: ...
    """
    engine = get_async_engine(os.getpid())
    async with engine.raw_connection() as conn:
        # conn 就是 asyncmy 的连接（DBAPI connection）
        yield conn
