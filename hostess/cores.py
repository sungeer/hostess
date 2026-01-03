import asyncio
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from hostess import tasks


@asynccontextmanager
async def lifespan(app):
    db_url = 'mysql+asyncmy://user:password@127.0.0.1:3306/testdb?charset=utf8mb4'

    app.state.db = create_async_engine(
        db_url,
        echo=False,
        pool_size=5,  # 常驻 5 条连接
        max_overflow=10,  # 高峰额外最多再开 10 条
        pool_timeout=30,  # 取连接等待 30s 失败就报错
        pool_recycle=1800,  # 回收重连
        pool_pre_ping=True,  # 避免拿到失效连接
        pool_use_lifo=True,  # 复用热连接
    )

    ts = tasks.tasks
    bg_tasks = []

    for t in ts:
        bg_task = asyncio.create_task(t(app))
        bg_tasks.append(bg_task)

    try:
        yield
    finally:
        for bg_task in bg_tasks:
            bg_task.cancel()

        await asyncio.gather(*bg_tasks, return_exceptions=True)

        await app.state.db.dispose()


# cors
origins = [
    'http://127.0.0.1:8000',  # 后端应用使用的端口
    'http://127.0.0.1:8080',  # 前端应用使用的端口
]

middleware = [
    Middleware(
        CORSMiddleware,  # type: ignore
        allow_origins=origins,  # ['*']
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    ),
]
