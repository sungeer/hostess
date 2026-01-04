from hostess.services import task
from hostess.utils import jsonify


async def get_tasks(request):
    db = request.app.state.db
    tasks = await task.get_tasks(db)
    return jsonify(tasks)


# 持久化暂停
async def pause_task(request):
    body = await request.json()
    task_id = body.get('task_id')
    db = request.app.state.db
    db_task = await task.pause_task(db, task_id)
    task_key = db_task.get('task_key')
    is_paused = db_task.get('is_paused')
    if task_key and is_paused:
        setattr(request.app.state, f'{task_key}_is_pause', 1)
    return jsonify()


# 持久化启用
async def run_task(request):
    body = await request.json()
    task_id = body.get('task_id')
    db = request.app.state.db
    db_task = await task.run_task(db, task_id)
    task_key = db_task.get('task_key')
    is_paused = db_task.get('is_paused')
    if task_key and is_paused:
        setattr(request.app.state, f'{task_key}_is_pause', 0)
    return jsonify()


# 临时停止
async def stop_tasks(request):
    setattr(request.app.state, 'is_exit', 1)
    return jsonify()


# 取消 临时停止
async def start_tasks(request):
    setattr(request.app.state, 'is_exit', 0)
    return jsonify()
