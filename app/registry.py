from __future__ import annotations
from dataclasses import dataclass
from typing import Awaitable, Callable
import importlib
import logging
import pkgutil

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class TaskSpec:
    name: str
    factory: Callable[["App"], Awaitable[None]]


def discover_tasks(package_name: str = "app.tasks") -> list[TaskSpec]:
    pkg = importlib.import_module(package_name)
    tasks: list[TaskSpec] = []

    for m in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
        mod = importlib.import_module(m.name)
        mod_tasks = getattr(mod, "TASKS", None)
        if not mod_tasks:
            continue
        for t in mod_tasks:
            tasks.append(t)

    # 按 name 排序，日志更稳定
    tasks.sort(key=lambda x: x.name)
    log.info("Discovered %d tasks from %s", len(tasks), package_name)
    return tasks
