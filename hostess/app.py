import asyncio
import signal
import sys

import asyncmy
from asyncmy.cursors import DictCursor
import httpx


class Config:
    def __init__(self):
        pass


class Resources:
    def __init__(self, db_pool, httpx_client):
        self.db_pool = db_pool
        self.httpx_client = httpx_client


async def open_resources(cfg):
    db_pool = await asyncmy.create_pool(
        host=cfg.mysql_host,
        port=cfg.mysql_port,
        user=cfg.mysql_user,
        password=cfg.mysql_password,
        db=cfg.mysql_db,
        minsize=cfg.mysql_min_size,
        maxsize=cfg.mysql_max_size,
        cursorclass=DictCursor,
    )

    limits = httpx.Limits(
        max_keepalive_connections=cfg.http_max_keepalive,
        max_connections=cfg.http_max_connections,
    )

    httpx_client = httpx.AsyncClient(
        timeout=httpx.Timeout(cfg.http_timeout_s),
        limits=limits,
    )

    return Resources(db_pool=db_pool, httpx_client=httpx_client)


def install_signal_handlers(stop_event):
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


async def task_a(stop):
    while not stop.is_set():
        print('a')
        await wait_stop(1, stop)


async def task_b(stop):
    while not stop.is_set():
        print('b')
        await wait_stop(2, stop)


async def task_c(stop):
    while not stop.is_set():
        print('c')
        await wait_stop(5, stop)


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
            tg.create_task(task_a(self.stop_event))
            tg.create_task(task_b(self.stop_event))
            tg.create_task(task_c(self.stop_event))

            await self.stop_event.wait()


async def main_async():
    cfg = Config()
    res = await open_resources(cfg)
    stop_event = asyncio.Event()
    install_signal_handlers(stop_event)

    app = Application(cfg, res, stop_event)
    await app.run()


def main():
    asyncio.run(main_async())


main()
