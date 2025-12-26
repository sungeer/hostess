import logging
from dataclasses import dataclass

import anyio

from .config import Config
from .logging_setup import setup_logging
from .resources import Resources, open_resources, close_resources
from .registry import TaskSpec, discover_tasks

log = logging.getLogger(__name__)


@dataclass
class App:
    cfg: Config
    res: Resources
    stop_event: anyio.Event


class TaskTracker:
    """
    追踪任务退出，用于“无轮询地”等待所有任务在 grace period 内完成。
    """

    def __init__(self, total: int):
        self.total = total
        self._done = 0
        self._lock = anyio.Lock()
        self.all_done = anyio.Event()

        if total == 0:
            self.all_done.set()

    async def mark_done(self) -> None:
        async with self._lock:
            self._done += 1
            if self._done >= self.total:
                self.all_done.set()

    @property
    def done(self) -> int:
        return self._done


async def _signal_watcher(stop_event: anyio.Event) -> None:
    """
    等待 SIGINT/SIGTERM，触发 stop_event。
    """
    import signal

    with anyio.open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
        async for sig in signals:
            if not stop_event.is_set():
                log.warning("Stop requested by signal: %s", getattr(sig, "name", sig))
                stop_event.set()
            break


async def main_async():
    cfg = Config()
    setup_logging(cfg.log_level)

    stop_event = anyio.Event()
    task_specs: list[TaskSpec] = discover_tasks("app.tasks")

    res = await open_resources(cfg)
    app = App(cfg=cfg, res=res, stop_event=stop_event)

    tracker = TaskTracker(total=len(task_specs))

    async def run_task(spec: TaskSpec) -> None:
        try:
            await spec.factory(app)
        finally:
            await tracker.mark_done()

    try:
        async with anyio.create_task_group() as tg:
            # 1) 信号监听
            tg.start_soon(_signal_watcher, stop_event)

            # 2) 启动所有任务
            for spec in task_specs:
                tg.start_soon(run_task, spec)

            # 3) 等待停止信号
            await stop_event.wait()

            # 4) 协作退出宽限期：无轮询，等到“所有任务退出”或“超时”
            log.info(
                "Stop event set. Waiting for tasks to exit (grace %.1fs)...",
                cfg.shutdown_grace_s,
            )
            with anyio.move_on_after(cfg.shutdown_grace_s) as grace_scope:
                await tracker.all_done.wait()

            if not grace_scope.cancel_called:
                log.info("All tasks exited gracefully (%d/%d).", tracker.done, tracker.total)
                # 退出 tg 上下文时会收拢所有任务（此时应该都结束了）
                return

            # 5) 超时：强制取消整个 TaskGroup，并在 force-cancel 超时内收拢
            log.warning(
                "Grace period expired. Forcing cancellation (%d/%d tasks exited).",
                tracker.done,
                tracker.total,
            )

            with anyio.fail_after(cfg.shutdown_force_cancel_s):
                tg.cancel_scope.cancel()
                # 关键点：取消后等待 all_done，让我们“知道”任务都结束了再退出
                await tracker.all_done.wait()

    finally:
        await close_resources(res)


def main() -> None:
    anyio.run(main_async)
