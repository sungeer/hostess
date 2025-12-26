import asyncio
from concurrent.futures import ThreadPoolExecutor

loop = asyncio.get_running_loop()

# 默认线程池（None）
result = await loop.run_in_executor(None, sync_func, *args)

# 或者自建线程池以控制 max_workers、线程命名等
executor = ThreadPoolExecutor(max_workers=10)
result = await loop.run_in_executor(executor, sync_func, *args)
