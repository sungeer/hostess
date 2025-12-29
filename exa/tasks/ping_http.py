# app/tasks/demo_ping_http.py
import logging
import anyio

from app.registry import TaskSpec
from app.runner import run_forever

log = logging.getLogger(__name__)


async def ping_http(app):
    async def unit():
        # 给每次请求一个额外超时保护也可以
        with anyio.fail_after(5):
            r = await app.res.http.get("https://example.com/")
            r.raise_for_status()
        log.info("ping_http ok: %s", r.status_code)

        # 控制循环频率（演示用）
        await anyio.sleep(2)

    await run_forever(name="ping_http", stop_event=app.stop_event, unit_of_work=unit)


TASKS = [
    TaskSpec(name="demo.ping_http", factory=ping_http),
]
