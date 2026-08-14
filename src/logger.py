from pathlib import Path

from loguru import logger

base_dir = Path(__file__).resolve().parent.parent

log_path = base_dir / 'logs/app_{time:YYYY-MM-DD}.log'


def setup_logger():
    logger.remove()

    fmt = '{time:YYYY-MM-DD HH:mm:ss} - {level} - {name}:{function}:{line} - {message}'

    logger.add(
        log_path,
        rotation='16:00',
        retention='7 days',
        format=fmt,
        encoding='utf-8',
        diagnose=False,
        backtrace=False,
        colorize=False,
        enqueue=False,  # 关闭异步记录
        level='INFO',
    )
