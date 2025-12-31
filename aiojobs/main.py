# main.py
from __future__ import annotations

import asyncio
import signal

from infra import load_infra_config
from runtime import Runtime
from tasks import ALL_TASKS


async def main() -> None:
    infra = load_infra_config()

    async with Runtime(infra=infra) as rt:
        rt.start_all(ALL_TASKS)

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for s in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(s, stop.set)
            except NotImplementedError:
                pass

        await stop.wait()
        # 退出 async with => stop_graceful_then_cancel()


if __name__ == "__main__":
    asyncio.run(main())
