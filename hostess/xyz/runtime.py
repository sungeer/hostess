# runtime.py

import asyncio

import httpx
from sqlalchemy.ext.asyncio import create_async_engine


class TaskSpec:
    def __init__(self, task_id, entry):
        self.task_id = task_id  # string
        self.entry = entry


class DBConfig:
    def __init__(self, switches):
        self.switches = switches  # dict


class Application:
    def __init__(self, config):
        self.config = config

        self.engine = None
        self.http = None

        self._settings = None
        self._tasks = {}

    async def __aenter__(self):
        self.engine = create_async_engine(
            self.config.db_url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=1800,
        )

        assert self.engine is not None

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

        assert self.http is not None

        await self.refresh_settings()

        self._tasks['_settings_refresher'] = asyncio.create_task(
            self._refresher_settings_task(),
            name='settings_refresher',
        )

        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.shutdown()

    @property
    def settings(self):
        # obj.settings
        return self._settings

    async def refresh_settings(self):
        """多种配置
        {
            'whitelist': ['u1','u2'],
            'thresholds': {'max_qps': 12, 'warn_latency_ms': 800},
            'switches': {'enable_sync': true}
        }
        """
        settings = {}
        sql_switch = '''
            SELECT id, task_name, status
            FROM switch
            WHERE is_deleted = 0
        '''
        async with self.engine.connect() as conn:
            result = await conn.execute(sql_switch)
            rows = result.mappings().all()
            switches = [dict(r) for r in rows]
        settings.update({'switches': switches})
        self._settings = settings

    async def _refresher_settings_task(self):
        while True:
            try:
                await asyncio.sleep(30)
                await self.refresh_settings()
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
