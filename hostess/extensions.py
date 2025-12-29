from contextlib import suppress, AsyncExitStack, asynccontextmanager

import httpx
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


def get_httpx_client(cfg):
    limits = httpx.Limits(
        max_keepalive_connections=cfg.httpx.max_keepalive,
        max_connections=cfg.httpx.max_connections,
    )
    httpx_client = httpx.AsyncClient(
        timeout=httpx.Timeout(cfg.httpx.timeout_s),
        limits=limits,
    )
    return httpx_client


async def closee_httpx(client):
    with suppress(Exception):
        await client.aclose()


# db pool
def get_dbpool(db_url):
    engine = create_async_engine(
        db_url,
        echo=False,
        pool_size=5,          # 常驻 5 条连接
        max_overflow=10,       # 高峰额外最多再开 10 条
        pool_timeout=30,       # 取连接等待 30s 失败就报错
        pool_recycle=1800,     # 回收重连
        pool_pre_ping=True,    # 避免拿到失效连接
        pool_use_lifo=True,    # 复用热连接
    )
    # await engine.dispose()  # 关闭连接池
    return engine


async def close_dbpool(engine):
    with suppress(Exception):
        await engine.dispose()


def get_dbconn(db_pool):
    session = async_sessionmaker(db_pool, expire_on_commit=False, class_=AsyncSession)
    return session


class Resources:
    def __init__(self, httpx_client, db_conn):
        self.httpx_client = httpx_client
        self.db_conn = db_conn


@asynccontextmanager
async def resources_handlers(cfg):
    async with AsyncExitStack() as stack:
        httpx_client = get_httpx_client(cfg)
        stack.push_async_callback(closee_httpx, httpx_client)

        db_url = f'mysql+asyncmy://{cfg.db.user}:{cfg.db.passwd}@{cfg.db.host}:{cfg.db.port}/{cfg.db.name}?charset=utf8mb4'
        db_pool = get_dbpool(db_url)
        stack.push_async_callback(close_dbpool, db_pool)

        db_conn = get_dbconn(db_pool)  # Session obj
        yield Resources(httpx_client=httpx_client, db_conn=db_conn)
