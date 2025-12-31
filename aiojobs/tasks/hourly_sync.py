# tasks/example_task.py
from __future__ import annotations

import asyncio

from runtime import TaskSpec, Runtime

TASK_ID = "example_task"


async def main(rt: Runtime) -> None:
    assert rt.http is not None

    while True:
        try:
            # 你手动改 DB 开关后，这里会在 refresh interval 内生效
            enabled = rt.dbcfg.switches.get("enable_sync", True)
            if not enabled:
                # “暂停模式”：不执行业务逻辑，但别空转
                await asyncio.sleep(0.5)
                continue

            # 白名单示例：为空表示不限制；非空则必须命中
            user_id = "u1"
            wl = rt.dbcfg.whitelist
            if wl and (user_id not in wl):
                await asyncio.sleep(0.5)
                continue

            # 阈值示例：控制节奏
            max_qps = rt.dbcfg.thresholds.get("max_qps", 10.0)
            delay = (1 / max_qps) if max_qps and max_qps > 0 else 0.2

            # 业务逻辑示例（外部请求）
            r = await rt.http.get("https://httpbin.org/get")
            _ = r.status_code

            await asyncio.sleep(delay)

        except asyncio.CancelledError:
            # 无脑 cancel 时要立刻退出
            raise
        except Exception:
            # 可接 logger.exception(...)
            await asyncio.sleep(1.0)


SPEC = TaskSpec(task_id=TASK_ID, entry=main)
