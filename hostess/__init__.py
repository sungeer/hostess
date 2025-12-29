import asyncio
from contextlib import AsyncExitStack
import signal
import sys

from hostess.settings import Config
from hostess import extensions


def signal_handlers(stop_event):
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


async def wait_stop(w_seconds, stop_event):
    interval_ms = w_seconds * 1000
    step_ms = 20
    waited_ms = 0
    while waited_ms < interval_ms and not stop_event.is_set():
        await asyncio.sleep(step_ms / 1000)
        waited_ms += step_ms


async def task_a(app):
    while not app.stop_event.is_set():
        print('a')
        await app.wait_stop(1)


async def task_b(app):
    while not app.stop_event.is_set():
        print('b')
        await app.wait_stop(2)


async def task_c(app):
    while not app.stop_event.is_set():
        print('c')
        await app.wait_stop(5)


class Application:
    def __init__(self, cfg, res, stop_event):
        self.cfg = cfg
        self.res = res
        self.stop_event = stop_event

    async def wait_stop(self, w_seconds):
        interval_ms = w_seconds * 1000
        step_ms = 20
        waited_ms = 0
        while waited_ms < interval_ms and not self.stop_event.is_set():
            await asyncio.sleep(step_ms / 1000)
            waited_ms += step_ms

    async def run(self):
        async with asyncio.TaskGroup() as tg:
            tg.create_task(task_a(self))
            tg.create_task(task_b(self))
            tg.create_task(task_c(self))

            await self.stop_event.wait()


async def main_async():
    stop_event = asyncio.Event()
    signal_handlers(stop_event)

    cfg = Config()

    async with extensions.resources_handlers(cfg) as res:
        app = Application(cfg, res, stop_event)
        await app.run()


def main():
    asyncio.run(main_async())


main()
