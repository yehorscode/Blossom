import datetime
import logging
import os
from pathlib import Path

from colorama import Back, Fore, Style


def get_log_dir():
    cache_home = os.getenv(
        "XDG_CACHE_HOME",
        os.path.join(os.path.expanduser("~"), ".cache")
    )
    log_dir = Path(cache_home) / "com.yehors.Blossom"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


LOG_DIR = get_log_dir()
LOG_FILE = LOG_DIR / "log.log"

logger = logging.getLogger("blossom")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s: %(message)s",
                         datefmt="%H:%M:%S")
    )
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s: %(message)s",
                         datefmt="%H:%M:%S")
    )
    logger.addHandler(console_handler)

    logger.propagate = False


# Colored console helpers
def critical(text: str):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    logger.critical(text)
    print(f"{Back.RED}{now} CRITICAL: {text}{Style.RESET_ALL}")


def error(text: str):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    logger.error(text)
    print(f"{Fore.RED}{now} ERROR: {text}{Style.RESET_ALL}")


def debug(text: str):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    logger.debug(text)
    print(f"{Fore.LIGHTWHITE_EX}{now} DEBUG: {text}{Style.RESET_ALL}")


def info(text: str):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    logger.info(text)
    print(f"{Fore.LIGHTCYAN_EX}{now} INFO: {text}{Style.RESET_ALL}")


def success(text: str):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    logger.info(text)
    print(f"{Fore.GREEN}{now} SUCCESS: {text}{Style.RESET_ALL}")
