# app/tasks/demo_db_heartbeat.py
import logging

import anyio

from app.registry import TaskSpec
from app.runner import run_forever

log = logging.getLogger(__name__)


async def db_heartbeat(app):
    async def unit():
        async with app.res.mysql.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                row = await cur.fetchone()
        log.info("db_heartbeat ok: %s", row)

        await anyio.sleep(5)

    await run_forever(name="db_heartbeat", stop_event=app.stop_event, unit_of_work=unit)


TASKS = [
    TaskSpec(name="demo.db_heartbeat", factory=db_heartbeat),
]
