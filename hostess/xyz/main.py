# main.py

import asyncio
import signal
import sys

from aiojobs.settings import load_config
from aiojobs.runtime import Application
from aiojobs.tasks import tasks


async def main():
    config = load_config()

    async with Application(config) as app:
        app.start_all(tasks)

        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()

        is_win = sys.platform.startswith('win')
        if is_win:
            def handler(signum, frame):  # noqa
                stop_event.set()

            signal.signal(signal.SIGINT, handler)
        else:
            def request_stop(signum: int):  # noqa
                stop_event.set()

            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, request_stop, sig)

        await stop_event.wait()
        # 退出 async with => stop_graceful_then_cancel()


asyncio.run(main())
