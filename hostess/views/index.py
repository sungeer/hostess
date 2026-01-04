from hostess import utils


async def healthz(request):
    return utils.jsonify()
