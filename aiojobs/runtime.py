# runtime.py

import asyncio

import httpx
from sqlalchemy.ext.asyncio import create_async_engine


class TaskSpec:
    def __init__(self, task_id, entry):
        self.task_id = task_id  # string
        self.entry = entry


class Application:
    def __init__(self, config):
        self.config = config

        self.engine = None
        self.http = None

        self._dbconfig = None
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

        await self.refresh_dbconfig()

        self._tasks['_dbconfig_refresher'] = asyncio.create_task(
            self._refresher_dbconfig_task(),
            name='dbconfig_refresher',
        )

        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.shutdown()

    @property
    def dbconfig(self):
        return self._dbconfig

    async def refresh_dbconfig(self):
        sql_str = '''
            SELECT 1
        '''
        async with self.engine.connect() as conn:
            result = await conn.execute(sql_str)
            rows = result.mappings().all()
            switchs = [dict(r) for r in rows]
        self._dbconfig = switchs

    async def _refresher_dbconfig_task(self):
        while True:
            try:
                await asyncio.sleep(30)
                await self.refresh_dbconfig()
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
