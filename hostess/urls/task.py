from starlette.routing import Router

from hostess.views import task

route = Router()

route.add_route('/get-tasks', task.get_tasks, ['POST'])
