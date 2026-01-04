from starlette.routing import Router

from hostess.views import task_view

task_url = Router()

task_url.add_route('/task', task_view.get_chat_id, ['POST'])
