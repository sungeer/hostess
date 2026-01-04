from starlette.routing import Router

from hostess.views import task_view

task_url = Router()

task_url.add_route('/get-tasks', task_view.get_tasks, ['POST'])
