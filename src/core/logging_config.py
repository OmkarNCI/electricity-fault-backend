import logging
import os

LOG_DIR = "/tmp"
LOG_FILE = os.path.join(LOG_DIR, "app.log")


def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if root_logger.handlers:
        root_logger.handlers.clear()

    file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def get_log_file_path() -> str:
    return LOG_FILE


def clear_log_file():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", encoding="utf-8"):
            pass