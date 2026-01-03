import asyncio

task_key = 'demo'


async def worker(app):
    while True:
        try:
            is_exit = app.state.is_exit
            if is_exit:
                return

            is_pause = get_switch(task_key)
            # v = getattr(app.state, "is_exit", False)
            # setattr(app.state, "is_exit", False)
            if is_pause:
                app.state.

            await asyncio.sleep(3)
        except asyncio.CancelledError:
            raise
        except (Exception,):
            pass
