from starlette.applications import Starlette

from hostess import cores


app = Starlette(
    routes = register_routes,
    middleware = cores.middleware,
    exception_handlers = register_errors,
    lifespan = cores.lifespan
)
