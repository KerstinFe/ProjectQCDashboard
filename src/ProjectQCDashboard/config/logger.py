import logging
from ProjectQCDashboard.config.paths import log_filepath
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from ProjectQCDashboard.config.RunningContainer import _is_running_in_container
from ProjectQCDashboard.config.loadParams import PARAMS
import time
from pythonjsonlogger.json import JsonFormatter

logging_str = "%(asctime)s: %(levelname)s: %(module)s: %(funcName)s: %(message)s"
DateFormat = "%Y-%m-%d %H:%M:%S"

loggerLevel = PARAMS.LOG_LEVEL

# Configure timezone for log timestamps
def berlin_time(*_ignored: object) -> time.struct_time:
    """
    Convert log timestamps to Berlin time (handles CET/CEST automatically).

    This function is used as a converter for log formatters to ensure all log timestamps
    are in the Europe/Berlin timezone, including daylight saving time adjustments.

    :param _ignored: Ignored arguments (for compatibility)
    :type _ignored: object
    :return: The current time in Berlin timezone as a struct_time
    :rtype: time.struct_time
    """
    berlin_tz = ZoneInfo('Europe/Berlin')
    return datetime.now(berlin_tz).timetuple()

formatter = JsonFormatter(
    fmt= logging_str,
    datefmt=DateFormat,
)
formatter.converter = berlin_time

# Always set up file logging
# In container with Gunicorn: this adds file handler alongside Gunicorn's handlers
# In local mode: this is the primary logging setup
file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
file_handler.setFormatter(formatter)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)

if _is_running_in_container():
    # In container with Gunicorn: use Gunicorn's logger and add file handler
    gunicorn_logger = logging.getLogger('gunicorn.error')
    gunicorn_logger.addHandler(file_handler)
    gunicorn_logger.setLevel(loggerLevel)
    # Also update Gunicorn's existing handlers to use Berlin time
    for handler in gunicorn_logger.handlers:
        handler.setFormatter(formatter)
else:
    # Local development: set up basic config with console and file
    logging.basicConfig(
        level=loggerLevel,
        handlers=[
            file_handler,
            stream_handler
        ]
    )
    

def get_configured_logger(name: str | None = None) -> logging.Logger:
    """
    Get a configured logger instance for the given module name.

    This function returns a logger that is pre-configured for either container or local development.
    In a container, it uses Gunicorn's logger; otherwise, it uses the standard Python logger.

    :param name: Name of the module for the logger (optional)
    :type name: str | None
    :return: Configured logger instance
    :rtype: logging.Logger
    """
    if _is_running_in_container():
        # Use Gunicorn's logger in container
        return logging.getLogger('gunicorn.error')
    else:
        # Use standard logger for local development
        return logging.getLogger(name or __name__)
