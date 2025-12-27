import asyncio, time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Entry:
    value: Any
    expire_at: float


class TTLCache:
    def __init__(self):
        self._data: Dict[str, Entry] = {}

    def get(self, key: str) -> Optional[Any]:
        e = self._data.get(key)
        if not e:
            return None
        if e.expire_at <= time.monotonic():
            self._data.pop(key, None)
            return None
        return e.value

    def set(self, key: str, value: Any, ttl: float) -> None:
        self._data[key] = Entry(value=value, expire_at=time.monotonic() + ttl)


cache = TTLCache()
_pool_lock = asyncio.Lock()


async def ensure_pool(app_obj) -> None:
    key, ttl = "pool:global", 300
    val = cache.get(key)
    if val is not None:
        app_obj.pool = val
        return

    async with _pool_lock:
        val = cache.get(key)
        if val is not None:
            app_obj.pool = val
            return
        db_result = await load_pool_from_mysql()
        cache.set(key, db_result, ttl)
        app_obj.pool = db_result
