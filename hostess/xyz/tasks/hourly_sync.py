# tasks/example_task.py

import asyncio

from aiojobs.runtime import TaskSpec

TASK_ID = "example_task"


async def main(app):
    assert app.http is not None

    while True:
        try:
            if app.dbswitch:
                await asyncio.sleep(0.5)
                continue

            if app.dbswitch:
                await asyncio.sleep(0.5)
                continue

            await asyncio.sleep(1)

        except asyncio.CancelledError:
            raise
        except (Exception,):
            await asyncio.sleep(1.0)


SPEC = TaskSpec(task_id=TASK_ID, entry=main)
