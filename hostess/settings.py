

class DBConfig:
    user = 'root'
    passwd = 'admin'
    host = '127.0.0.1'
    port = 3306
    name = 'viper'


class HttpxConfig:
    timeout_s = 10
    max_keepalive = 20
    max_connections = 100


class Config:
    db = DBConfig
    httpx = HttpxConfig
