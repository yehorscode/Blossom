import datetime
import logging
import os

from colorama import Back, Fore, Style

log_dir = "logs"
log_file = os.path.join(log_dir, "log.log")

os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger("blossom")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s: %(message)s", datefmt="%H:%M:%S")
    )
    logger.addHandler(file_handler)
    logger.propagate = False


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
