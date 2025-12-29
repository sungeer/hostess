from __future__ import annotations
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Config:
    # MySQL
    mysql_host: str = os.getenv("MYSQL_HOST", "127.0.0.1")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user: str = os.getenv("MYSQL_USER", "root")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "")
    mysql_db: str = os.getenv("MYSQL_DB", "test")

    mysql_min_size: int = int(os.getenv("MYSQL_POOL_MIN", "1"))
    mysql_max_size: int = int(os.getenv("MYSQL_POOL_MAX", "10"))

    # HTTP
    http_timeout_s: float = float(os.getenv("HTTP_TIMEOUT_S", "10"))
    http_max_keepalive: int = int(os.getenv("HTTP_MAX_KEEPALIVE", "20"))
    http_max_connections: int = int(os.getenv("HTTP_MAX_CONNECTIONS", "100"))

    # Lifecycle
    shutdown_grace_s: float = float(os.getenv("SHUTDOWN_GRACE_S", "15"))
    shutdown_force_cancel_s: float = float(os.getenv("SHUTDOWN_FORCE_CANCEL_S", "5"))

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
