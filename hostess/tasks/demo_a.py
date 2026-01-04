import asyncio
from datetime import datetime
import time

from hostess import models

task_key = 'demo_a'


async def worker(app):
    while True:
        try:
            if app.state.is_exit:
                setattr(app.state, f'{task_key}_run_status', 'exiting')
                await asyncio.sleep(3)
                continue

            is_pause = getattr(app.state, f'{task_key}_is_pause')
            if is_pause:
                setattr(app.state, f'{task_key}_run_status', 'pausing')
                await asyncio.sleep(3)
                continue

            setattr(app.state, f'{task_key}_run_status', 'running')

            t0 = time.perf_counter()

            await asyncio.sleep(0.3)

            print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

            dt = time.perf_counter() - t0
            print(f'func took {dt:.3f}s')

            await asyncio.sleep(3)
        except asyncio.CancelledError:
            raise
        except (Exception,):
            pass


tm = models.TaskModel(task_key, worker)
