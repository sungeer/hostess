import time
import hashlib

import httpx


def auth_key():
    key = '299095cc-1330-11e5-b06a-a45e60bec08b'  # 双方约定的 secret_key
    key_name = 'X-Auth-Key'

    ha = hashlib.md5(key.encode('utf-8'))
    time_span = time.time()

    ha.update(bytes('%s|%f' % (key, time_span), encoding='utf-8'))
    encryption = ha.hexdigest()
    result = '%s|%f' % (encryption, time_span)
    return {key_name: result}


def send_data(user_info):
    url = 'http://127.0.0.1:8000/auth.token'

    headers = {}
    headers.update(auth_key())

    with httpx.Client() as client:
        response = client.post(url=url, json=user_info, headers=headers)

    return response


if __name__ == '__main__':
    data = {
        'user_id': 123,
        'username': 'facai'
    }
    jwt_token = send_data(data)
    print(jwt_token)
