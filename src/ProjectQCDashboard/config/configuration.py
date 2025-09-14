from pathlib import Path
# from box import Box
from ProjectQCDashboard.config.paths import PACKAGE_ROOT, PACKAGE_LOCATION
from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.config.loadParams import load_params

logger = get_configured_logger(__name__)
# Application constants
APP_NAME = "ProjectQCDashboard"


PARAMS = load_params()

DATA_LOCATION = PARAMS.get('Params', {}).get('Folder')

# Derived configuration (combines internal config with external params)
DaysToMonitor = PARAMS.get('processing', {}).get('DaysToMonitor')
DaysToMonitor_notRunningProject = PARAMS.get('processing', {}).get('DaysToMonitor_notRunningProject')

TablesMetaData = PARAMS.get('data', {}).get('Tables_Metadata_db')
TablesMQQCData = PARAMS.get('data', {}).get('Tables_MQQC_db')
PollingIntervalSeconds = PARAMS.get('processing', {}).get('PollingIntervalSeconds')

# logger.info(f"Params{PARAMS}")
