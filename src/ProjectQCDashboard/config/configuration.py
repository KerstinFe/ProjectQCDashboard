from ProjectQCDashboard.config.loadParams import PARAMS
from collections import OrderedDict

TablesMetaData = PARAMS.data.Tables_Metadata_db
TablesMQQCData = PARAMS.data.Tables_MQQC_db

PollingIntervalSeconds = PARAMS.processing.PollingIntervalSeconds
ThresholdForTwoColumnsOfGraphs = PARAMS.processing.ThresholdForTwoColumnsOfGraphs
ThresholdForRollingMean = PARAMS.processing.ThresholdForRollingMean
UpdateLastXEntries = PARAMS.processing.UpdateLastXEntries

plot_config_seq = PARAMS.ColumnsDatabase.PLOT_CONFIG
PLOT_CONFIG = OrderedDict(plot_config_seq)
DB_CONFIG = PARAMS.ColumnsDatabase.DB_CONFIG

ROWS_Table = list(PARAMS.ColumnsDatabase.TABLE_CONFIG)
