"""
Demo: 单进程 asyncio 定时任务框架（50 个任务也适用）
- 资源：SQLAlchemy async engine（连接池） + httpx.AsyncClient（请求池）
- 任务：while True + 周期 sleep；支持 pause（开关）与 stop（进程退出）
- 开关：内存缓存 + 兜底定期从 DB 刷新（可选）
- 退出：优雅停止（stop_event）+ 超时后 cancel 强制收尾

依赖：
  pip install sqlalchemy asyncmy httpx
"""

from __future__ import annotations

import asyncio
import signal
import time
from dataclasses import dataclass, field
from typing import Callable, Awaitable

import httpx
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text


# ----------------------------
# 你的 DB engine 配置
# ----------------------------
db_url = "mysql+asyncmy://user:password@127.0.0.1:3306/testdb?charset=utf8mb4"

engine = create_async_engine(
    db_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    pool_use_lifo=True,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


# ----------------------------
# 开关表（示例）
# ----------------------------
# 建议表结构（示意）：
# CREATE TABLE job_switch (
#   job_id VARCHAR(128) PRIMARY KEY,
#   enabled TINYINT(1) NOT NULL DEFAULT 1,
#   updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
# );
#
# 如果你已有表/字段名不同，把 SQL 改一下即可。


@dataclass
class Runtime:
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    # 手工改库兜底刷新间隔：你可以改成 10/30/60
    switch_refresh_interval: float = 30.0

    enabled_cache: dict[str, bool] = field(default_factory=dict)
    cache_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    tasks: dict[str, asyncio.Task] = field(default_factory=dict)

    http: httpx.AsyncClient | None = None

    async def start(self) -> None:
        # 1) 初始化 HTTP 请求池
        self.http = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            headers={"User-Agent": "async-worker-demo/1.0"},
        )

        # 2) 启动前全量加载一次开关到缓存
        await self.refresh_switches(full=True)

        # 3) 启动兜底刷新任务（防手工改库）
        self.tasks["_switch_refresher"] = asyncio.create_task(
            self._switch_refresher_loop(), name="switch_refresher"
        )

        # 4) 启动你的 jobs（示例：2 个；你可以扩到 50 个）
        self.spawn_interval_job("hourly_sync", period=3.0, coro=self.job_hourly_sync)
        self.spawn_interval_job("pull_metrics", period=3.0, coro=self.job_pull_metrics)

    async def stop(self, *, grace: float = 3.0) -> None:
        # 通知所有循环尽快退出
        self.stop_event.set()

        # 先等一小段时间让它们自然退出（不强杀）
        await self._wait_tasks(grace=grace)

        # 超时还没退出的：cancel 强制结束
        pending = [t for t in self.tasks.values() if not t.done()]
        for t in pending:
            t.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        # 关闭 http 客户端（请求池）
        if self.http is not None:
            await self.http.aclose()

        # 关闭 DB engine（连接池）
        await engine.dispose()

    # ----------------------------
    # 开关缓存
    # ----------------------------
    async def is_enabled(self, job_id: str) -> bool:
        async with self.cache_lock:
            return self.enabled_cache.get(job_id, True)

    async def set_enabled(self, job_id: str, enabled: bool) -> None:
        """
        标准“写路径更新缓存”：推荐你的管理命令/脚本走这里，
        这样开关变更可近乎实时生效，而不是等定时刷新。
        """
        async with SessionLocal() as session:
            # MySQL UPSERT 写法（需要 job_id 为主键或唯一键）
            await session.execute(
                text(
                    """
                    INSERT INTO job_switch (job_id, enabled)
                    VALUES (:job_id, :enabled)
                    ON DUPLICATE KEY UPDATE enabled = VALUES(enabled)
                    """
                ),
                {"job_id": job_id, "enabled": 1 if enabled else 0},
            )
            await session.commit()

        async with self.cache_lock:
            self.enabled_cache[job_id] = enabled

    async def refresh_switches(self, *, full: bool = True) -> None:
        """
        兜底刷新：从 DB 拉取开关状态到内存。
        full=True：全量刷新（简单可靠）
        想做增量的话可以加 last_sync + updated_at 条件。
        """
        async with SessionLocal() as session:
            rows = (await session.execute(text("SELECT job_id, enabled FROM job_switch"))).all()

        fresh: dict[str, bool] = {job_id: bool(enabled) for job_id, enabled in rows}

        async with self.cache_lock:
            # 只覆盖 DB 中存在的键；不存在的 job 默认 True
            # 如果你希望“DB 没记录就视为禁用”，把默认改一下即可
            self.enabled_cache.update(fresh)

    async def _switch_refresher_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=self.switch_refresh_interval)
                break
            except asyncio.TimeoutError:
                pass

            try:
                await self.refresh_switches(full=True)
            except Exception:
                # 刷新失败不应让整个后台退出
                print("[switch_refresher] refresh failed")
                # 这里建议 logger.exception(...)
                continue

    # ----------------------------
    # Job 管理：interval 循环 + pause/stop + 防重入
    # ----------------------------
    def spawn_interval_job(
        self,
        job_id: str,
        period: float,
        coro: Callable[[str], Awaitable[None]],
    ) -> None:
        if job_id in self.tasks:
            raise RuntimeError(f"job {job_id} already exists")

        task = asyncio.create_task(
            self._interval_loop(job_id=job_id, period=period, coro=coro),
            name=f"job:{job_id}",
        )
        self.tasks[job_id] = task

    async def _interval_loop(
        self,
        *,
        job_id: str,
        period: float,
        coro: Callable[[str], Awaitable[None]],
    ) -> None:
        """
        - 用 loop.time() 做 tick，减少漂移
        - stop_event 用 wait_for(timeout=...)，能“立刻”响应退出
        - running_lock 防重入：上次没跑完，本次跳过（避免堆积）
        """
        running_lock = asyncio.Lock()
        loop = asyncio.get_running_loop()
        next_ts = loop.time() + period

        while not self.stop_event.is_set():
            timeout = max(0.0, next_ts - loop.time())
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=timeout)
                break
            except asyncio.TimeoutError:
                pass

            next_ts += period

            # pause（软暂停）：不执行主体逻辑
            if not await self.is_enabled(job_id):
                continue

            # 防重入：如果还在跑，就跳过本轮
            if running_lock.locked():
                continue

            async with running_lock:
                try:
                    await coro(job_id)
                except asyncio.CancelledError:
                    # 允许取消快速传播
                    raise
                except Exception:
                    print(f"[{job_id}] failed")
                    # 这里建议 logger.exception(...)

    async def _wait_tasks(self, *, grace: float) -> None:
        """
        等待所有 job 在 grace 时间内退出（不包含已完成的）。
        """
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline:
            pending = [t for t in self.tasks.values() if not t.done()]
            if not pending:
                return
            await asyncio.sleep(0.05)

    # ----------------------------
    # 示例 Jobs
    # ----------------------------
    async def job_hourly_sync(self, job_id: str) -> None:
        # DB 操作示例
        async with SessionLocal() as session:
            # 仅示例：轻量查询
            await session.execute(text("SELECT 1"))
            # 真实业务这里可能有 insert/update
            await session.commit()

        # HTTP 示例
        assert self.http is not None
        r = await self.http.get("https://httpbin.org/get")
        _ = r.status_code
        # print(f"[{job_id}] ok {r.status_code}")

    async def job_pull_metrics(self, job_id: str) -> None:
        # 另一个 job 示例
        async with SessionLocal() as session:
            await session.execute(text("SELECT NOW()"))
        # 不一定要 commit（SELECT 不需要）
        # 这里只做演示


# ----------------------------
# 进程入口：信号优雅退出
# ----------------------------
async def main() -> None:
    rt = Runtime(switch_refresh_interval=30.0)

    # 捕获 SIGINT/SIGTERM
    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, rt.stop_event.set)
        except NotImplementedError:
            # Windows 某些模式不支持
            pass

    await rt.start()

    # 这里就是你的“主阻塞点”
    await rt.stop_event.wait()

    # 退出清理
    await rt.stop(grace=2.0)


if __name__ == "__main__":
    asyncio.run(main())