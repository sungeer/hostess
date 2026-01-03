from typing import Any

import orjson
from starlette.responses import JSONResponse


# 字符串


def obj_to_json(data: Any) -> str:
    payload = orjson.dumps(data)  # bytes
    return payload.decode('utf-8')  # string


def json_to_obj(json_str: str) -> Any:
    return orjson.loads(json_str)


# 字节


def obj_to_jsonb(data: Any) -> bytes:
    return orjson.dumps(data)


def jsonb_to_obj(json_bytes: bytes) -> Any:
    return orjson.loads(json_bytes)


class Response(JSONResponse):
    def render(self, content: Any) -> bytes:
        return obj_to_jsonb(content)


class ResponseModel:
    def __init__(self):
        self.code = 0
        self.msg = 'ok'
        self.data = None

    def to_dict(self):
        resp_dict = {
            'code': self.code,
            'msg': self.msg,
            'data': self.data
        }
        return resp_dict


def jsonify(*args, **kwargs):
    if args and kwargs:
        raise TypeError('jsonify() behavior undefined when passed both args and kwargs')
    elif len(args) == 1:
        content = args[0]
    else:
        content = kwargs or list(args)  # {}
    response = ResponseModel()
    response.data = content
    response = response.to_dict()
    return Response(response)


def abort(error_code, error_message):
    response = ResponseModel()
    response.code = error_code
    response.msg = error_message
    response = response.to_dict()
    return Response(response)
