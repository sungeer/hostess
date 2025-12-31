import asyncio
import signal
import sys
from dataclasses import dataclass
from types import SimpleNamespace
from contextlib import asynccontextmanager, AsyncExitStack
from typing import Awaitable, Callable, Any

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import text


# -------------------------
# Config
# -------------------------
@dataclass(frozen=True)
class Config:
    db_url: str
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800
    pool_pre_ping: bool = True
    pool_use_lifo: bool = True

    poll_interval: float = 3.0
    db_concurrency: int = 10  # 限制同一时刻打 DB 的协程数（建议 <= pool_size+max_overflow）


class App:
    def __init__(self, config, lifespan):
        self.config = config
        self.state = SimpleNamespace()
        self._lifespan = lifespan
        self._workers = []

    def add_worker(self, name, worker):
        self._workers.append((name, worker))

    async def _run_worker(self, name, fn):
        try:
            await fn(self)
        except asyncio.CancelledError:
            # 记录 worker 被取消
            raise
        except Exception as e:
            # fail-fast：raise，让 TaskGroup 取消全部
            print(f"[{name}] crashed: {e!r}")
            pass

    @staticmethod
    def _install_signal_handlers(stop_event):
        is_win = sys.platform.startswith('win')
        loop = asyncio.get_running_loop()

        def request_stop(signum: int):  # noqa
            stop_event.set()

        def handler(signum, frame):  # noqa
            stop_event.set()

        if is_win:
            signal.signal(signal.SIGINT, handler)
        else:
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, request_stop, sig)

    async def _serve_forever(self):
        stop_event = asyncio.Event()
        self.state.stop_event = stop_event

        self._install_signal_handlers(stop_event)

        async with asyncio.TaskGroup() as tg:
            for name, fn in self._workers:
                tg.create_task(self._run_worker(name, fn))

            await stop_event.wait()

    async def run(self):
        async with self._lifespan(self):
            await self._serve_forever()


def make_engine(config):
    return create_async_engine(
        config.db_url,
        echo=config.echo,
        pool_size=config.pool_size,
        max_overflow=config.max_overflow,
        pool_timeout=config.pool_timeout,
        pool_recycle=config.pool_recycle,
        pool_pre_ping=config.pool_pre_ping,
        pool_use_lifo=config.pool_use_lifo,
    )


async def warmup(engine):
    async with engine.connect() as conn:
        await conn.execute(text('SELECT 1'))


@asynccontextmanager
async def lifespan(app):
    async with AsyncExitStack() as stack:
        engine = make_engine(app.config)
        stack.push_async_callback(engine.dispose)

        await warmup(engine)

        app.state.engine = engine
        # app.state.db_sem = asyncio.Semaphore(app.config.db_concurrency)

        yield app
        # 退出时：先返回到 App.run()，TaskGroup 已收敛，再到这里 dispose engine


async def polling_worker(app, name):
    while not app.state.stop_event.is_set():
        try:
            async with app.state.engine.connect() as conn:
                await conn.execute(text("SELECT NOW()"))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            # 自愈策略：记录错误，下一轮再试（你也可以加指数退避）
            print(f"[{name}] error: {e!r}")

        await asyncio.sleep(sleep_s)


async def main():
    config = Config(
        db_url="mysql+asyncmy://user:password@127.0.0.1:3306/testdb?charset=utf8mb4",
        poll_interval=3.0,
        db_concurrency=10,
    )

    app = App(config=config, lifespan=lifespan)

    # 注册 50 个 worker
    for i in range(50):
        worker_name = f"poller-{i:02d}"
        app.add_worker(worker_name, lambda app, n=worker_name: polling_worker(app, n))

    await app.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
