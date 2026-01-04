from hostess.services import task as task_service
from hostess.utils import jsonify
from hostess import tasks as task_apps


async def get_tasks(request):
    tasks = task_apps.tasks
    task_keys = [t.task_id for t in tasks]
    memory_status = {}
    for task_key in task_keys:
        status = getattr(request.app.state, f'{task_key}_run_status')
        memory_status.update({task_key:status})
    db = request.app.state.db
    tasks = await task_service.get_tasks(db)
    for task in tasks:
        task_key = task['task_key']
        status = memory_status.get(task_key)
        task['memory_status'] = status
    return jsonify(tasks)


async def get_task(request):
    body = await request.json()
    task_id = body.get('task_id')
    db = request.app.state.db
    db_task = await task_service.get_task(db, task_id)
    task_key = db_task['task_key']
    status = getattr(request.app.state, f'{task_key}_run_status')
    db_task['memory_status'] = status
    print(db_task)
    return jsonify(db_task)


# 持久化暂停
async def pause_task(request):
    body = await request.json()
    task_id = body.get('task_id')
    db = request.app.state.db
    db_task = await task_service.pause_task(db, task_id)
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
    db_task = await task_service.run_task(db, task_id)
    task_key = db_task.get('task_key')
    is_paused = db_task.get('is_paused')
    if task_key and not is_paused:
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
