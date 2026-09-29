from __future__ import annotations

import logging


def configure_logging(level: str = "INFO", *, app_name: str = "rest_api_pipeline") -> logging.Logger:
    logger = logging.getLogger(app_name)
    logger.setLevel(level.upper())
    if logger.handlers:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    return logger
