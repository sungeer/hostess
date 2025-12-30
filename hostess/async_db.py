from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

db_url = 'mysql+asyncmy://user:password@127.0.0.1:3306/testdb?charset=utf8mb4'

engine = create_async_engine(
    db_url,
    echo=False,
    pool_size=5,  # 常驻 5 条连接
    max_overflow=10,  # 高峰额外最多再开 10 条
    pool_timeout=30,  # 取连接等待 30s 失败就报错
    pool_recycle=1800,  # 回收重连
    pool_pre_ping=True,  # 避免拿到失效连接
    pool_use_lifo=True,  # 复用热连接
)


# await engine.dispose()  # 关闭


async def query_one():
    sql = text('''
        SELECT id, name, age
        FROM user
        WHERE id = :id
    ''')
    async with engine.connect() as conn:
        result = await conn.execute(sql, {'id': 1})
        row = result.mappings().first()  # RowMapping | None
        # row = result.mappings().one()  # 没有或多于一条都会抛异常
        return dict(row) if row else None


async def query_many():
    sql = text('''
        SELECT id, name, age
        FROM user
        WHERE age >= :min_age
        ORDER BY id
        LIMIT :limit
    ''')
    async with engine.connect() as conn:
        result = await conn.execute(sql, {'min_age': 18, 'limit': 10})
        rows = result.mappings().all()  # list[RowMapping]
        return [dict(r) for r in rows]


async def insert_user(name, age):
    sql = text('INSERT INTO user(name, age) VALUES (:name, :age)')
    async with engine.begin() as conn:
        result = await conn.execute(sql, {'name': name, 'age': age})
        return result.rowcount, result.lastrowid


async def update_user_name(user_id, new_name):
    sql = text('UPDATE user SET name = :name WHERE id = :id')
    async with engine.begin() as conn:
        result = await conn.execute(sql, {'name': new_name, 'id': user_id})
        return result.rowcount


async def delete_user(user_id):
    sql = text('DELETE FROM user WHERE id = :id')
    async with engine.begin() as conn:
        result = await conn.execute(sql, {'id': user_id})
        return result.rowcount
