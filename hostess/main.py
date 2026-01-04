from starlette.applications import Starlette

from hostess import cores


app = Starlette(
    routes = cores.routes,
    middleware = cores.middleware,
    exception_handlers = cores.exception_handlers,
    lifespan = cores.lifespan
)
