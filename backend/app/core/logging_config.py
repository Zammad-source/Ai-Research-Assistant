import logging
import os
import sys
from logging.handlers import RotatingFileHandler

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# setup_logging() is called on import, so it can run more than once in a
# process (reload, tests). Adding handlers each time duplicated every log line.
_configured = False


def _file_logging_enabled() -> bool:
    """
    File logging is off unless explicitly requested.

    Railway (and most containers) capture stdout and give the process an
    ephemeral filesystem, so writing a rotating log file there burns disk for
    logs nobody will ever read. Locally it stays on by default, which is what
    the existing workflow expects.
    """
    flag = os.getenv("LOG_TO_FILE")
    if flag is not None:
        return flag.strip().lower() in {"1", "true", "yes", "on"}
    return os.getenv("RAILWAY_ENVIRONMENT") is None


def setup_logging():
    global _configured
    if _configured:
        return logging.getLogger()

    os.makedirs(LOG_DIR, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if _file_logging_enabled():
        try:
            file_handler = RotatingFileHandler(
                LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except OSError as e:
            # A read-only or full filesystem must never stop the app booting.
            logging.getLogger(__name__).warning(
                "File logging disabled, could not open %s: %s", LOG_FILE, e
            )

    # uvicorn installs its own handlers; leaving them on top of ours prints
    # every access log line twice.
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("httpx").setLevel(logging.WARNING)

    _configured = True
    return root_logger