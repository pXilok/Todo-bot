"""Настройка стандартного logging."""

import logging.config

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(level: str) -> None:
    """Конфигурирует корневой логгер и логгеры uvicorn в едином формате."""
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"default": {"format": LOG_FORMAT}},
            "handlers": {
                "console": {"class": "logging.StreamHandler", "formatter": "default"},
            },
            "root": {"handlers": ["console"], "level": level},
            "loggers": {
                "uvicorn.access": {"level": level, "propagate": True, "handlers": []},
                "sqlalchemy.engine": {"level": "WARNING", "propagate": True},
            },
        }
    )