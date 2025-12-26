import os
from functools import lru_cache

import MySQLdb
from MySQLdb.cursors import DictCursor
from sqlalchemy.pool import QueuePool

from viper import settings


def create_db_connect():
    return MySQLdb.connect(
        host=settings.database_host,
        user=settings.database_username,
        passwd=settings.database_password,
        db=settings.database_name,
        charset="utf8mb4",
        cursorclass=DictCursor,
    )


@lru_cache
def get_db_pool(pid: int):
    return QueuePool(
        creator=create_db_connect,
        pool_size=5,
        max_overflow=10,
        timeout=30,
        recycle=1800,
        pre_ping=True,
    )


def get_db_conn():
    pool = get_db_pool(os.getpid())
    return pool.connect()
