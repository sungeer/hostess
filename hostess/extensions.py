import asyncmy
from asyncmy.cursors import DictCursor
import httpx


async def get_db_pool(cfg):
    db_pool = await asyncmy.create_pool(
        host=cfg.mysql_host,
        port=cfg.mysql_port,
        user=cfg.mysql_user,
        password=cfg.mysql_password,
        db=cfg.mysql_db,
        minsize=cfg.mysql_min_size,
        maxsize=cfg.mysql_max_size,
        pool_recycle=1800,
        charset='utf8mb4',
        cursorclass=DictCursor,
    )
    return db_pool


async def get_httpx_client(cfg):
    limits = httpx.Limits(
        max_keepalive_connections=cfg.http_max_keepalive,
        max_connections=cfg.http_max_connections,
    )
    httpx_client = httpx.AsyncClient(
        timeout=httpx.Timeout(cfg.http_timeout_s),
        limits=limits,
    )
    return httpx_client


class DBConnection:
    def __init__(self):
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = create_dbconn()
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cursor.close()
        self.conn.close()

    def commit(self):
        try:
            self.conn.commit()
        except (Exception,):
            self.conn.rollback()

    def begin(self):
        self.conn.begin()

    def execute(self, sql_str, values=None):
        try:
            self.cursor.execute(sql_str, values)
        except Exception:
            self.rollback()
            self.close()
            raise
