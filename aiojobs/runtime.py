# runtime.py

import asyncio

import httpx
from sqlalchemy.ext.asyncio import create_async_engine

from dbcfg import DbConfigSnapshot, load_runtime_config


class TaskSpec:
    def __init__(self, task_id, entry):
        self.task_id = task_id  # string
        self.entry = entry


class Application:
    def __init__(self, config):
        self.config = config

        self.engine = None
        self.http = None

        self._dbcfg = DbConfigSnapshot.default()
        self._tasks = {}

    async def __aenter__(self):
        self.engine = create_async_engine(
            self.config.db_url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=1800,
        )

        limits = httpx.Limits(
            max_connections=self.config.http_max_connections,
            max_keepalive_connections=self.config.http_max_keepalive,
        )
        timeout = httpx.Timeout(self.config.http_timeout_s)

        self.http = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            proxy=self.config.http_proxy,
            headers={"User-Agent": f"async-worker/1.0 ({self.config.app_env})"},
        )

        await self.refresh_dbcfg()  # 加载数据库动态配置

        self._tasks['_dbcfg_refresher'] = asyncio.create_task(
            self._dbcfg_refresher_loop(),
            name='dbcfg_refresher',
        )

        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.shutdown()

    @property
    def dbcfg(self):
        return self._dbcfg

    async def refresh_dbcfg(self) -> None:
        async with self.session() as s:
            snap = await load_runtime_config(s)
        self._dbcfg = snap

    # 刷新数据库动态配置
    async def _dbcfg_refresher_loop(self):
        while True:
            try:
                await asyncio.sleep(30)
                await self.refresh_dbcfg()
            except asyncio.CancelledError:
                raise
            except (Exception,):
                continue

    def start_all(self, specs):
        for spec in specs:
            if spec.task_id in self._tasks:
                raise RuntimeError(f'duplicate task_id: {spec.task_id}')
            self._tasks[spec.task_id] = asyncio.create_task(
                spec.entry(self),
                name=f'task:{spec.task_id}',
            )

    async def shutdown(self):
        tasks = [t for t in self._tasks.values() if not t.done()]
        for t in tasks:
            t.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

        if self.http is not None:
            await self.http.aclose()
            self.http = None

        if self.engine is not None:
            await self.engine.dispose()
            self.engine = None
