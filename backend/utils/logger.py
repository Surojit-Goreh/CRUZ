"""
Shared logger setup. Writes to backend/data/logs/cruz.log and echoes to
console, so tool executions — especially anything that touches disk —
leave an audit trail you can check after the fact.
"""
import logging

from utils.paths import LOGS_ROOT

_LOG_FILE = LOGS_ROOT / "cruz.log"
_configured_loggers = set()


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if name not in _configured_loggers:
        logger.setLevel(logging.INFO)

        file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
        console_handler = logging.StreamHandler()

        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.propagate = False

        _configured_loggers.add(name)

    return logger
