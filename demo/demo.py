import asyncio
import signal
import sys


async def wait_stop(w_seconds, stop_event):
    interval_ms = w_seconds * 1000
    step_ms = 20
    waited_ms = 0
    while waited_ms < interval_ms and not stop_event.is_set():
        await asyncio.sleep(step_ms / 1000)
        waited_ms += step_ms


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


def install_signal_handlers(stop):
    is_win = sys.platform.startswith('win')
    loop = asyncio.get_running_loop()

    def request_stop(signum: int):
        stop.set()

    def handler(signum, frame):
        stop.set()

    if is_win:
        signal.signal(signal.SIGINT, handler)
    else:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, request_stop, sig)


async def run_all():
    stop = asyncio.Event()
    install_signal_handlers(stop)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(task_a(stop))
        tg.create_task(task_b(stop))
        tg.create_task(task_c(stop))

        await stop.wait()


def main():
    asyncio.run(run_all())


if __name__ == "__main__":
    main()
