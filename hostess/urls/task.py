from starlette.routing import Router

from hostess.views import task

route = Router()

route.add_route('/get-tasks', task.get_tasks, ['POST'])
route.add_route('/get-task', task.get_task, ['POST'])
# 持久化暂停
route.add_route('/pause-task', task.pause_task, ['POST'])
# 持久化运行
route.add_route('/run-task', task.run_task, ['POST'])
# 临时停止全部 用于发版
route.add_route('/stop-tasks', task.stop_tasks, ['POST'])
# 取消 临时停止全部
route.add_route('/start-tasks', task.start_tasks, ['POST'])
