from sqlalchemy import text


async def get_tasks(db):
    sql_str = text('''
        SELECT
            t.task_name, t.task_key, s.is_paused, t.updated_at
        FROM
            task t
            LEFT JOIN switch s
                ON s.task_id = t.id
        WHERE
            t.is_deleted = 0
    ''')
    async with db.connect() as conn:
        result = await conn.execute(sql_str)
        rows = result.mappings().all()
    return [dict(r) for r in rows]


async def pause_task(db, task_id):
    sql_str = text('''
        UPDATE
            switch
        SET
            is_paused = 1
        WHERE
            task_id = :task_id
    ''')
    async with db.begin() as conn:
        await conn.execute(sql_str, {'task_id': task_id})

    sql_str = text('''
        SELECT
            t.task_name, t.task_key, s.is_paused
        FROM
            task t
            LEFT JOIN switch s
                ON s.task_id = t.id
        WHERE
            t.id = :task_id
    ''')
    async with db.connect() as conn:
        result = await conn.execute(sql_str, {'task_id': task_id})
        row = result.mappings().first()
    return dict(row) if row else {}


async def run_task(db, task_id):
    sql_str = text('''
        UPDATE
            switch
        SET
            is_paused = 0
        WHERE
            task_id = :task_id
    ''')
    async with db.begin() as conn:
        await conn.execute(sql_str, {'task_id': task_id})

    sql_str = text('''
        SELECT
            t.task_name, t.task_key, s.is_paused
        FROM
            task t
            LEFT JOIN switch s
                ON s.task_id = t.id
        WHERE
            t.id = :task_id
    ''')
    async with db.connect() as conn:
        result = await conn.execute(sql_str, {'task_id': task_id})
        row = result.mappings().first()
    return dict(row) if row else {}
