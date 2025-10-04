from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.config.loadParams import load_params


logger = get_configured_logger(__name__)

PARAMS = load_params()

DATA_LOCATION = PARAMS.get('Params', {}).get('Folder')
TablesMetaData = PARAMS.get('data', {}).get('Tables_Metadata_db')
TablesMQQCData = PARAMS.get('data', {}).get('Tables_MQQC_db')

DaysToMonitor = PARAMS.get('processing', {}).get('DaysToMonitor')
DaysToMonitor_notRunningProject = PARAMS.get('processing', {}).get('DaysToMonitor_notRunningProject')
PollingIntervalSeconds = PARAMS.get('processing', {}).get('PollingIntervalSeconds')
ThresholdForTwoColumnsOfGraphs = PARAMS.get('processing', {}).get('ThresholdForTwoColumnsOfGraphs')

