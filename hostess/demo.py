# app.py
from contextlib import asynccontextmanager
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

import asyncio
import logging

logger = logging.getLogger(__name__)


# ---- 你的协程任务：会使用 app.state 中挂载的配置/依赖 ----
async def job_refresh_cache(app: Starlette):
    cfg = app.state.config
    # 示例：用 cfg 做事情
    logger.info("refresh_cache start, env=%s", cfg["env"])
    await asyncio.sleep(0.2)
    logger.info("refresh_cache done")


async def job_sync_data(app: Starlette, source: str):
    cfg = app.state.config
    logger.info("sync_data start, source=%s, token=%s", source, cfg["token"][:4] + "****")
    await asyncio.sleep(0.2)
    logger.info("sync_data done")


def create_scheduler(app: Starlette) -> AsyncIOScheduler:
    """
    创建并配置调度器。把 app 放进任务参数，确保每次执行都能拿到 app.state。
    """
    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    # Interval 示例：每 10 秒执行一次
    scheduler.add_job(
        job_refresh_cache,
        trigger=IntervalTrigger(seconds=10),
        kwargs={"app": app},
        id="refresh_cache",
        replace_existing=True,
        max_instances=1,  # 避免同一任务并发重入（常见需求）
        coalesce=True,  # 堆积时合并执行
        misfire_grace_time=30  # 允许错过触发后 30s 内补执行
    )

    # Cron 示例：每天 03:30 执行
    scheduler.add_job(
        job_sync_data,
        trigger=CronTrigger(hour=3, minute=30),
        kwargs={"app": app, "source": "warehouse"},
        id="sync_data",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300
    )

    return scheduler


@asynccontextmanager
async def lifespan(app: Starlette):
    # 1) 挂载配置/依赖（示例）
    app.state.config = {
        "env": "prod",
        "token": "YOUR_TOKEN_VALUE",
    }

    # 2) 创建并启动 APScheduler（使用同一个 event loop）
    scheduler = create_scheduler(app)
    app.state.scheduler = scheduler
    scheduler.start()
    logger.info("scheduler started")

    try:
        yield
    finally:
        # 3) 关闭调度器（优雅）
        scheduler.shutdown(wait=False)
        logger.info("scheduler stopped")


app = Starlette(lifespan=lifespan)


@app.route("/health")
async def health(_):
    return JSONResponse({"ok": True})
