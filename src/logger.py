from pathlib import Path

from loguru import logger

base_dir = Path(__file__).resolve().parent.parent

log_path = base_dir / 'logs/hostess_{time:YYYY-MM-DD}.log'

_LEVEL_ABBR = {
    'TRACE': 'TRC',
    'DEBUG': 'DBG',
    'INFO': 'INF',
    'SUCCESS': 'SUC',
    'WARNING': 'WRN',
    'ERROR': 'ERR',
    'CRITICAL': 'CRT'
}


def _patch_record(record):
    record['level'].name = _LEVEL_ABBR.get(record['level'].name, record['level'].name)


def setup_logger():
    logger.remove()

    logger.configure(patcher=_patch_record)

    fmt = '{time:HH:mm:ss.SSS} | {level} | {message} ({name}:{line})'

    logger.add(
        log_path,
        rotation='00:00',
        retention='7 days',
        format=fmt,
        encoding='utf-8',
        diagnose=False,
        backtrace=False,
        colorize=False,
        enqueue=False,  # 关闭异步记录
        level='INFO',
    )
