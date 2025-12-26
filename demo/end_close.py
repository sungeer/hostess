import asyncio
import os
import signal

stop_event = asyncio.Event()


def _request_stop():
    stop_event.set()


async def main():
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            # Windows ProactorEventLoop 等可能不支持
            pass

    try:
        # 启动你的任务
        worker = asyncio.create_task(your_worker_loop(stop_event))

        # 等待退出信号
        await stop_event.wait()

        # 让任务收尾
        worker.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker
    finally:
        await get_async_engine(os.getpid()).dispose()
