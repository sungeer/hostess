from __future__ import annotations
import logging
from dataclasses import dataclass

import anyio

from .config import Config
from .logging_setup import setup_logging
from .resources import Resources, open_resources, close_resources
from .registry import TaskSpec, discover_tasks
from .runner import run_forever

log = logging.getLogger(__name__)


@dataclass
class App:
    cfg: Config
    res: Resources
    stop_event: anyio.Event


async def _run_all_tasks(app: App, task_specs: list[TaskSpec]) -> None:
    async with anyio.create_task_group() as tg:
        for spec in task_specs:
            # 每个任务模块自己负责调用 run_forever（推荐），这里直接启动 factory
            tg.start_soon(spec.factory, app)

        # 主协程等待停止信号
        await app.stop_event.wait()
        # 退出 task_group 作用域时会取消子任务（兜底）。
        # 但我们更希望子任务检测 stop_event 自己退出，所以这里只是触发退出条件。


async def _lifespan() -> None:
    cfg = Config()
    setup_logging(cfg.log_level)

    stop_event = anyio.Event()
    task_specs = discover_tasks("app.tasks")

    async def _on_signal():
        if not stop_event.is_set():
            log.warning("Stop requested (signal).")
            stop_event.set()

    # 用 anyio 的信号接收（POSIX 下可靠；Windows 下 SIGTERM 支持有限）
    async with anyio.create_task_group() as signal_tg:
        async def _signal_watcher():
            with anyio.open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
                async for _ in signals:
                    await _on_signal()
                    break

        import signal
        signal_tg.start_soon(_signal_watcher)

        res = await open_resources(cfg)
        app = App(cfg=cfg, res=res, stop_event=stop_event)

        try:
            # 第一阶段：协作退出（grace）
            with anyio.move_on_after(cfg.shutdown_grace_s) as grace_scope:
                await _run_all_tasks(app, task_specs)

            if grace_scope.cancel_called:
                log.warning("Grace period expired (%.1fs). Forcing cancellation...", cfg.shutdown_grace_s)
                stop_event.set()

                # 第二阶段：兜底取消（强制）
                with anyio.fail_after(cfg.shutdown_force_cancel_s):
                    # 重新跑一个 taskgroup 等待退出是不对的；
                    # 这里的关键是：_run_all_tasks 的 task group 退出时会 cancel 子任务。
                    # 但我们已经离开 _run_all_tasks 了怎么办？
                    # ——所以我们需要把 task_group 生命周期包在这里，而不是 _run_all_tasks 内部。
                    pass
        finally:
            await close_resources(res)

        # 结束信号 watcher
        signal_tg.cancel_scope.cancel()


async def main_async() -> None:
    # 关键：把任务组放在主生命周期里，这样超时后我们能直接 cancel_scope.cancel()
    cfg = Config()
    setup_logging(cfg.log_level)

    stop_event = anyio.Event()
    task_specs = discover_tasks("app.tasks")

    import signal

    async def on_stop():
        if not stop_event.is_set():
            log.warning("Stop requested.")
            stop_event.set()

    async def signal_watcher():
        with anyio.open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
            async for _ in signals:
                await on_stop()
                break

    res = await open_resources(cfg)
    app = App(cfg=cfg, res=res, stop_event=stop_event)

    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(signal_watcher)

            # 启动全部任务
            for spec in task_specs:
                tg.start_soon(spec.factory, app)

            # 等停止
            await stop_event.wait()

            # 协作退出宽限期：让任务自行结束（它们应检测 stop_event）
            with anyio.move_on_after(cfg.shutdown_grace_s) as scope:
                # 等待所有任务结束的一个简单方式：轮询 task group 不行；
                # 更推荐：任务在退出时会自然结束，task group 会在我们退出作用域时一起 cancel。
                # 所以这里采用：在 grace 内短睡，给任务机会结束；到期再强制 cancel。
                while True:
                    await anyio.sleep(0.2)

            if scope.cancel_called:
                log.warning("Grace period expired (%.1fs). Cancelling task group...", cfg.shutdown_grace_s)
                tg.cancel_scope.cancel()
                # tg.cancel_scope.cancel() 会取消所有任务；退出 async with 时收拢

    finally:
        await close_resources(res)


def main() -> None:
    anyio.run(main_async)
