# main.py

import asyncio
import signal
import sys

from infra import load_infra_config
from runtime import Runtime
from tasks import tasks


async def main():
    infra = load_infra_config()

    async with Runtime(infra=infra) as rt:
        rt.start_all(tasks)

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()

        def request_stop(signum: int):  # noqa
            stop.set()

        def handler(signum, frame):  # noqa
            stop.set()

        is_win = sys.platform.startswith('win')
        if is_win:
            signal.signal(signal.SIGINT, handler)
        else:
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, request_stop, sig)

        await stop.wait()
        # 退出 async with => stop_graceful_then_cancel()


asyncio.run(main())
