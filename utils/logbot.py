import logging
import queue
from logging.handlers import QueueHandler

from settings_files._global import DEBUG_STATUS


def below_warning(record):
    if record.levelno < 30:
        return True
    return False


class LogBot:
    q = queue.Queue()
    # noinspection SpellCheckingInspection
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(module)s/%(funcName)s %(lineno)d: %(message)s")
    base_logger = logging.getLogger()
    logger = base_logger.getChild("BotLog")
    logger.setLevel(logging.DEBUG)

    to_filter = logging.Filter("DEBUG ONLY")

    if DEBUG_STATUS():
        log_stream = logging.StreamHandler()
        log_stream.setFormatter(formatter)
        log_stream.setLevel(logging.DEBUG)
        logger.addHandler(log_stream)

    logfile = logging.FileHandler("./data/bot.log", encoding="UTF-8")
    logfile.setFormatter(formatter)
    logfile.setLevel(logging.WARNING)

    log_queue = QueueHandler(q)
    log_queue.setFormatter(formatter)
    log_queue.setLevel(logging.WARNING)

    logger.addHandler(logfile)

    logger.addHandler(log_queue)

    logger.debug("Logger active")
