import logging
from typing import Dict, Any, Optional
from ProjectQCDashboard.config.paths import PACKAGE_LOCATION
from pathlib import Path
import os
import sys

logging_str = "[%(asctime)s: %(levelname)s: %(module)s: %(message)s]"
DateFormat = "%Y-%m-%d %H:%M:%S"

log_dir = Path(PACKAGE_LOCATION/ "logs" ).as_posix()
os.makedirs(log_dir, exist_ok=True) 

log_filepath = Path(PACKAGE_LOCATION/ "logs" / "message.log").as_posix()


def get_configured_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a configured logger instance.
    :param name: Name of the module for the logger
    :type name: str
    :return: Configured logger instance
    :rtype: logging.Logger
    """
    if name is None:
        name = __name__

    logging.basicConfig(
        level=logging.INFO,
        format=logging_str,
        datefmt=DateFormat,

        handlers=[
        logging.FileHandler(log_filepath),
        logging.StreamHandler(sys.stdout)
    ]
    )
    return logging.getLogger(name)

