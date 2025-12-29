import asyncio
from contextlib import AsyncExitStack, asynccontextmanager


class DemoResource:
    def __init__(self, name: str):
        self.name = name

    async def open(self):
        print(f"[resource] open: {self.name}")

    async def aclose(self):
        print(f"[resource] close: {self.name}")


@asynccontextmanager
async def lifespan():
    print("[lifespan] enter (startup begin)")
    async with AsyncExitStack() as stack:
        # 打开资源 + 登记清理
        r1 = DemoResource("R1")
        await r1.open()
        stack.push_async_callback(r1.aclose)

        r2 = DemoResource("R2")
        await r2.open()
        stack.push_async_callback(r2.aclose)

        print("[lifespan] startup done, yielding resources")
        try:
            yield {"r1": r1, "r2": r2}
        finally:
            # 注意：这里的 finally 会先执行，然后退出 AsyncExitStack 才会真正 close
            print("[lifespan] exit (shutdown begin)")
    # 退出 AsyncExitStack 后，已执行所有 push_async_callback
    print("[lifespan] shutdown done (all resources closed)")


async def worker(name, resources):
    print(f"[{name}] start")
    try:
        while True:
            print(f"[{name}] tick")
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print(f"[{name}] cancelled")
        raise
    finally:
        print(f"[{name}] finally (cleanup in task)")


async def main():
    async with lifespan() as resources:
        print(resources)
        async with asyncio.TaskGroup() as tg:
            tg.create_task(worker("w1", resources))
            tg.create_task(worker("w2", resources))

            # 一直运行，直到 Ctrl+C
            await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # asyncio.run 在 Ctrl+C 时会负责取消 main 里的任务并收尾；
        # 这里捕获只是为了不打印一长串 traceback
        print("[main] KeyboardInterrupt (process exiting)")
