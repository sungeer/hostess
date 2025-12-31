# dbcfg.py

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class DbConfigSnapshot:
    """
    任务通过 rt.dbcfg 拿到的是这个快照对象（不可变），避免被任务误改。
    """
    whitelist: set[str]
    thresholds: dict[str, float]
    switches: dict[str, bool]
    version: int  # 用于调试/观测配置更新

    @staticmethod
    def default() -> "DbConfigSnapshot":
        return DbConfigSnapshot(
            whitelist=set(),
            thresholds={},
            switches={},
            version=0,
        )


def _as_set(v: Any) -> set[str]:
    if v is None:
        return set()
    if isinstance(v, (list, tuple, set)):
        return {str(x) for x in v}
    return {str(v)}


def _as_thresholds(v: Any) -> dict[str, float]:
    if isinstance(v, dict):
        out: dict[str, float] = {}
        for k, val in v.items():
            try:
                out[str(k)] = float(val)
            except Exception:
                continue
        return out
    return {}


def _as_switches(v: Any) -> dict[str, bool]:
    if isinstance(v, dict):
        out: dict[str, bool] = {}
        for k, val in v.items():
            out[str(k)] = bool(val)
        return out
    return {}


async def load_runtime_config(session: AsyncSession) -> DbConfigSnapshot:
    """
    表结构建议（单行 JSON）：
      CREATE TABLE runtime_config (
        id INT PRIMARY KEY,
        config_json JSON NOT NULL,
        version BIGINT NOT NULL DEFAULT 1,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
      );
    约定 id=1

    config_json 示例：
      {
        "whitelist": ["u1","u2"],
        "thresholds": {"max_qps": 12, "warn_latency_ms": 800},
        "switches": {"enable_sync": true}
      }
    """
    row = (
        await session.execute(
            text("SELECT config_json, version FROM runtime_config WHERE id=1")
        )
    ).first()

    if not row:
        return DbConfigSnapshot.default()

    config_json, version = row

    if config_json is None:
        cfg: Any = {}
    elif isinstance(config_json, dict):
        cfg = config_json
    elif isinstance(config_json, (str, bytes)):
        cfg = json.loads(config_json)
    else:
        cfg = {}

    return DbConfigSnapshot(
        whitelist=_as_set(cfg.get("whitelist")),
        thresholds=_as_thresholds(cfg.get("thresholds")),
        switches=_as_switches(cfg.get("switches")),
        version=int(version or 0),
    )
