import logging
import logging.config
import logging.handlers
from pathlib import Path


def configure_logging(log_dir: str = "/app/logs") -> None:
    """Set up console + rotating file logging. Safe to call multiple times.

    Falls back to console-only logging when log_dir is not writable (e.g. CI or any
    non-Docker environment), so importing the app never fails on logging setup.
    """
    handlers: dict = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    }
    root_handlers = ["console"]
    file_logging_error: str | None = None
    try:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
    except OSError as e:
        file_logging_error = str(e)
    else:
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": f"{log_dir}/app.log",
            "maxBytes": 10_485_760,  # 10 MB
            "backupCount": 5,
            "formatter": "default",
            "encoding": "utf-8",
        }
        root_handlers.append("file")

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            },
            "handlers": handlers,
            "root": {
                "level": "INFO",
                "handlers": root_handlers,
            },
        }
    )
    if file_logging_error:
        logging.getLogger(__name__).warning(
            "File logging disabled (%s not writable: %s); using console only.",
            log_dir,
            file_logging_error,
        )
