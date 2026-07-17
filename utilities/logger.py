"""
logger.py
---------
One log file per test run.

Rules from the requirements:
  * every step is logged (pass AND fail)
  * only the newest 5 log files are kept
  * the file name ends with  <datetime>_version#   e.g.  etl_20260716_143005_v7.log

Usage:
    from utilities.logger import get_logger
    log = get_logger()
    log.info("something happened")
"""

import os
import re
import glob
import logging
from datetime import datetime

from utilities import config_loader

_LOGGER = None                     # cached logger for the whole run
LOG_FILE_PATH = None               # the file this run is writing to


def _logs_dir():
    settings = config_loader.get_settings()
    path = config_loader.abs_path(settings["paths"]["logs"])
    os.makedirs(path, exist_ok=True)
    return path


def _next_version(logs_dir, cycle):
    """
    Return the next version number, cycling 1..`cycle` and restarting at 1.

    The "latest" version comes from the most recently written log file (by
    modification time), NOT the highest number: once the numbers wrap around
    (..., 9, 10, 1, 2, ...) the max on disk is no longer the newest run.
    """
    files = glob.glob(os.path.join(logs_dir, "etl_*_v*.log"))
    if not files:
        return 1
    newest = max(files, key=os.path.getmtime)
    m = re.search(r"_v(\d+)\.log$", newest)
    last = int(m.group(1)) if m else 0
    return (last % cycle) + 1


def _prune_old_logs(logs_dir, keep):
    """Delete the oldest log files so that only `keep` remain."""
    files = glob.glob(os.path.join(logs_dir, "etl_*_v*.log"))
    files.sort(key=os.path.getmtime)                # oldest first
    while len(files) > keep:
        old = files.pop(0)
        try:
            os.remove(old)
        except OSError:
            pass


def get_logger():
    """Create (once) and return the run logger."""
    global _LOGGER, LOG_FILE_PATH
    if _LOGGER is not None:
        return _LOGGER

    settings = config_loader.get_settings()
    logs_dir = _logs_dir()
    keep = settings["logging"].get("keep_versions", 5)
    cycle = settings["logging"].get("version_cycle", 10)
    level = getattr(logging, settings["logging"].get("level", "INFO").upper(), logging.INFO)

    version = _next_version(logs_dir, cycle)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"etl_{stamp}_v{version}.log"
    LOG_FILE_PATH = os.path.join(logs_dir, file_name)

    logger = logging.getLogger("etl_framework")
    logger.setLevel(level)
    logger.handlers.clear()          # avoid duplicate handlers on re-import

    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    # keep only the newest 5 log files (this run's file counts as one)
    _prune_old_logs(logs_dir, keep)

    logger.info("=" * 70)
    logger.info(f"NEW ETL TEST RUN STARTED  ->  {file_name}")
    logger.info("=" * 70)
    _LOGGER = logger
    return logger
