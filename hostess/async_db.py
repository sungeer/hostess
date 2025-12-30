from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
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

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def query_as_dicts():
    sql = text('''
        SELECT
            id, name, age
        FROM
            user
        WHERE
            age >= :min_age
        ORDER BY id
        LIMIT :limit
    ''')
    async with SessionLocal() as session:
        result = await session.execute(sql, {"min_age": 18, "limit": 10})
        return [dict(r) for r in result.mappings().all()]


async def do_update():
    async with SessionLocal() as session:
        async with session.begin():  # 事务开始
            result = await session.execute(
                text("UPDATE user SET name=:name WHERE id=:id"),
                {"name": "new", "id": 1},
            )
            # 不需要手动 commit()
            return result.rowcount
        # 如果上面任何一步抛异常 -> 自动 rollback
