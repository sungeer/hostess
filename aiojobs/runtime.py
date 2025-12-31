# runtime.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable

import httpx
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from dbcfg import DbConfigSnapshot, load_runtime_config
from infra import InfraConfig


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    entry: Callable[["Runtime"], Awaitable[None]]


@dataclass
class Runtime:
    infra: InfraConfig

    # --- resources ---
    engine: AsyncEngine | None = None
    sessionmaker: async_sessionmaker[AsyncSession] | None = None
    http: httpx.AsyncClient | None = None

    # --- tasks ---
    tasks: dict[str, asyncio.Task] = field(default_factory=dict)

    # --- stop/pause control ---
    pause_event: asyncio.Event = field(default_factory=asyncio.Event)  # set => RUN
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)

    # --- db config cache ---
    _dbcfg: DbConfigSnapshot = field(default_factory=DbConfigSnapshot.default)
    _dbcfg_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    # 刷新间隔（运行型配置才刷新）
    dbcfg_refresh_interval: float = 30.0
    enable_dbcfg_refresher: bool = True

    async def __aenter__(self) -> "Runtime":
        # pause_event: 默认允许运行
        self.pause_event.set()

        self.engine = create_async_engine(
            self.infra.db_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True,
            pool_use_lifo=True,
        )
        self.sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)

        limits = httpx.Limits(
            max_connections=self.infra.http_max_connections,
            max_keepalive_connections=self.infra.http_max_keepalive,
        )
        timeout = httpx.Timeout(self.infra.http_timeout_s)
        self.http = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            proxy=self.infra.http_proxy,
            headers={"User-Agent": f"async-worker/1.0 ({self.infra.app_env})"},
        )

        # 启动加载一次 dbcfg（白名单/阈值/开关）
        await self.refresh_dbcfg()

        if self.enable_dbcfg_refresher:
            self.tasks["_dbcfg_refresher"] = asyncio.create_task(
                self._dbcfg_refresher_loop(),
                name="dbcfg_refresher",
            )

        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop_graceful_then_cancel()

    def session(self) -> AsyncSession:
        if self.sessionmaker is None:
            raise RuntimeError("Runtime not started")
        return self.sessionmaker()

    # -------- dbcfg access --------
    @property
    def dbcfg(self) -> DbConfigSnapshot:
        """
        任务里用 rt.dbcfg.whitelist 拿快照。
        注意：这是“当前快照引用”；快照对象本身不可变。
        """
        return self._dbcfg

    async def refresh_dbcfg(self) -> None:
        async with self.session() as s:
            snap = await load_runtime_config(s)
        async with self._dbcfg_lock:
            self._dbcfg = snap

    async def _dbcfg_refresher_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self.dbcfg_refresh_interval)
                await self.refresh_dbcfg()
            except asyncio.CancelledError:
                raise
            except Exception:
                # logger.exception(...)
                continue

    # -------- task control --------
    def start_all(self, specs: list[TaskSpec]) -> None:
        for spec in specs:
            if spec.task_id in self.tasks:
                raise RuntimeError(f"duplicate task_id: {spec.task_id}")
            self.tasks[spec.task_id] = asyncio.create_task(
                spec.entry(self),
                name=f"task:{spec.task_id}",
            )

    def pause_all(self) -> None:
        """
        停前全暂停：让任务在合适的“安全点”停住（由任务里 await rt.pause_event.wait() 配合）。
        """
        self.pause_event.clear()

    def resume_all(self) -> None:
        self.pause_event.set()

    async def stop_graceful_then_cancel(self) -> None:
        """
        你的策略：
        1) 停前全暂停（可选，但这里默认执行）
        2) 停时立即 cancel（强制）
        """
        self.stop_event.set()
        self.pause_all()  # 让任务尽快进入暂停点（如果任务配合的话）

        # 立即 cancel（核心）
        to_cancel = [t for t in self.tasks.values() if not t.done()]
        for t in to_cancel:
            t.cancel()
        if to_cancel:
            await asyncio.gather(*to_cancel, return_exceptions=True)

        if self.http is not None:
            await self.http.aclose()
            self.http = None

        if self.engine is not None:
            await self.engine.dispose()
            self.engine = None
            self.sessionmaker = None
