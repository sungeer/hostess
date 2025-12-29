from __future__ import annotations
import logging
import random
from dataclasses import dataclass

import anyio

log = logging.getLogger(__name__)


@dataclass
class Backoff:
    initial: float = 0.5
    maximum: float = 30.0
    multiplier: float = 2.0
    jitter: float = 0.1

    current: float = 0.5

    def reset(self) -> None:
        self.current = self.initial

    def next_sleep(self) -> float:
        base = self.current
        self.current = min(self.current * self.multiplier, self.maximum)
        return base + random.random() * self.jitter


async def run_forever(
        *,
        name: str,
        stop_event: anyio.Event,
        unit_of_work,  # async () -> None
        backoff: Backoff | None = None,
) -> None:
    """
    标准的任务循环模板：
    - 观察 stop_event 协作退出
    - 异常 -> 记录 -> 退避
    """
    b = backoff or Backoff(current=Backoff().initial)

    log.info("Task started: %s", name)
    try:
        while not stop_event.is_set():
            try:
                await unit_of_work()
                b.reset()
            except (anyio.get_cancelled_exc_class(),):
                # 取消属于正常退出路径
                raise
            except Exception:
                sleep_s = b.next_sleep()
                log.exception("Task error: %s (backoff %.2fs)", name, sleep_s)
                # stop_event 触发后，不要再睡满退避时间，尽快退出
                with anyio.move_on_after(sleep_s) as scope:
                    await stop_event.wait()
                if stop_event.is_set():
                    break
    finally:
        log.info("Task stopped: %s", name)
