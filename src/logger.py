import sys

from loguru import logger


def setup_logger():
    logger.remove()

    fmt = '{time:YYYY-MM-DD HH:mm:ss} - {level} - {name}:{function}:{line} - {message}'

    logger.add(
        sink=sys.stdout,
        format=fmt,
        diagnose=False,
        backtrace=False,
        colorize=False,
        enqueue=False,
        level='INFO',
    )
