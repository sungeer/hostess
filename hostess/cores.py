import asyncio
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route, Mount

from hostess import tasks
from hostess.views import index
from hostess.urls import task_url

routes = [
    Route('/', endpoint=index.healthz, methods=['GET']),
    Mount('/task', app=task_url.chat_url)
]


async def get_db_pauses(db):
    sql_str = '''
        a
    '''
    async with db.connect() as conn:
        result = await conn.execute(sql_str)
        rows = result.mappings().all()
    result = [dict(r) for r in rows]
    return {r['task_key']: r['is_paused'] for r in result}


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

    app.state.is_exit = 0  # 全局任务退出 0运行 1退出

    db_pauses = await get_db_pauses(app.state.db)

    ts = tasks.tasks  # task_model_obj
    bg_tasks = []

    for t in ts:
        t = t.entry  # task func
        task_key = t.task_id

        setattr(app.state, f'{task_key}_run_status', 'running')  # 初始化运行状态

        db_pause = db_pauses.get(task_key, 0)
        if db_pause:
            setattr(app.state, f'{task_key}_is_pause', 1)
        else:
            setattr(app.state, f'{task_key}_is_pause', 0)  # 每个任务的持久化启停 0运行 1停止

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
