from dataclasses import dataclass
import logging

import asyncmy
from asyncmy.pool import Pool

import httpx

from .config import Config

log = logging.getLogger(__name__)


@dataclass
class Resources:
    mysql: Pool
    http: httpx.AsyncClient


async def open_resources(cfg: Config) -> Resources:
    """
    创建全局共享资源：DB连接池 + HTTP client
    """
    log.info("Opening resources...")

    pool = await asyncmy.create_pool(
        host=cfg.mysql_host,
        port=cfg.mysql_port,
        user=cfg.mysql_user,
        password=cfg.mysql_password,
        db=cfg.mysql_db,
        minsize=cfg.mysql_min_size,
        maxsize=cfg.mysql_max_size,
        autocommit=True,
    )

    limits = httpx.Limits(
        max_keepalive_connections=cfg.http_max_keepalive,
        max_connections=cfg.http_max_connections,
    )
    http = httpx.AsyncClient(
        timeout=httpx.Timeout(cfg.http_timeout_s),
        limits=limits,
    )

    log.info("Resources opened (mysql pool + http client).")
    return Resources(mysql=pool, http=http)


async def close_resources(res: Resources) -> None:
    log.info("Closing resources...")

    try:
        await res.http.aclose()
    except Exception:
        log.exception("Error closing http client")

    try:
        res.mysql.close()
        await res.mysql.wait_closed()
    except Exception:
        log.exception("Error closing mysql pool")

    log.info("Resources closed.")
