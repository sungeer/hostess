# infra.py
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class InfraConfig:
    app_env: str  # local/dev/prod
    db_url: str
    http_timeout_s: float
    http_max_connections: int
    http_max_keepalive: int
    http_proxy: str | None


def load_infra_config() -> InfraConfig:
    """
    你要求：连接类配置放在 py 文件中。
    这里用 APP_ENV 做分支即可。你也可以改成读取机器 hostname 等。
    """
    app_env = os.getenv("APP_ENV", "prod").lower()

    if app_env == "local":
        return InfraConfig(
            app_env=app_env,
            db_url="mysql+asyncmy://user:password@127.0.0.1:3306/testdb?charset=utf8mb4",
            http_timeout_s=10.0,
            http_max_connections=50,
            http_max_keepalive=10,
            http_proxy=None,
        )

    # 默认 prod（示例）
    return InfraConfig(
        app_env=app_env,
        db_url="mysql+asyncmy://user:password@10.0.0.10:3306/proddb?charset=utf8mb4",
        http_timeout_s=10.0,
        http_max_connections=200,
        http_max_keepalive=50,
        http_proxy=None,
    )
