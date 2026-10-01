import logging
# import sys
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
    datefmt = '%H:%M:%S'

    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    # console_handler = logging.StreamHandler(sys.stdout)
    # console_handler.setFormatter(formatter)
    # root_logger.addHandler(console_handler)

    file_handler = TimedRotatingFileHandler(
        log_file,
        when='midnight',
        backupCount=3,
        encoding='utf-8'
    )

    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
