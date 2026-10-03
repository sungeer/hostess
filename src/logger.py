import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent

log_file = base_dir / 'logs/hostess.log'


def setup_logger():
    root_logger = logging.getLogger()

    logging.addLevelName(logging.DEBUG, 'DBG')
    logging.addLevelName(logging.INFO, 'INF')
    logging.addLevelName(logging.WARNING, 'WRN')
    logging.addLevelName(logging.ERROR, 'ERR')
    logging.addLevelName(logging.CRITICAL, 'CRT')

    root_logger.setLevel(logging.INFO)

    logging.getLogger('httpx2').setLevel(logging.WARNING)

    fmt = '%(asctime)s | %(levelname)s | %(message)s (%(name)s:%(lineno)d)'

    formatter = logging.Formatter(fmt=fmt)

    file_handler = TimedRotatingFileHandler(
        log_file,
        when='midnight',
        backupCount=3,
        encoding='utf-8'
    )

    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
