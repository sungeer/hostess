# tasks/example_task.py
from __future__ import annotations

import asyncio

from aiojobs.runtime import Runtime, TaskSpec

TASK_ID = "example_task"


async def main(rt: Runtime) -> None:
    assert rt.http is not None

    while True:
        try:
            # 安全点：支持“停前全暂停”
            await rt.pause_event.wait()

            # 使用 DB 运行型配置快照
            wl = rt.dbcfg.whitelist
            enabled = rt.dbcfg.switches.get("enable_sync", True)
            max_qps = rt.dbcfg.thresholds.get("max_qps", 10.0)

            if not enabled:
                await asyncio.sleep(1)
                continue

            # 业务示例：白名单判断
            user_id = "u1"
            if wl and user_id not in wl:
                await asyncio.sleep(1)
                continue

            # 外部请求示例（httpx 配置来自 infra.py，不热更新）
            r = await rt.http.get("https://httpbin.org/get")
            _ = r.status_code

            # 你自己的节奏控制
            await asyncio.sleep(1 / max_qps if max_qps > 0 else 1)

        except asyncio.CancelledError:
            raise
        except Exception:
            # logger.exception(...)
            await asyncio.sleep(1)


ts = TaskSpec(task_id=TASK_ID, entry=main)
