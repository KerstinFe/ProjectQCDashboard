import os
from datetime import datetime
from ProjectQCDashboard.helper.database import Database_Call
from ProjectQCDashboard.helper.common import SplitProjectName, GetLastDateToMonitor,GetLastModificationDate
from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.config.configuration import DaysToMonitor_notRunningProject
from typing import Any,  Union
from pathlib import Path

logger = get_configured_logger(__name__)

def CleanUp_csvFiles(CSVFolder: Union[str, Path], metadata_db_path: Union[str, Path], stop_event: Any) -> None:

    """Clean up CSV files in the specified folder.
    :param CSVFolder: Path to the folder containing CSV files
    :type CSVFolder: Union[str, Path]
    :param metadata_db_path: Path to the metadata SQLite database file
    :type metadata_db_path: Union[str, Path]
    :param stop_event: Event to signal stopping the cleanup process
    :type stop_event: Any
    :return: None
    :rtype: None
    """

    files = os.listdir(CSVFolder)
    ProjectIDs_Dict = Database_Call(metadata_db_path).getProjectNamesDict("regex")
    
    OneDayOld = GetLastDateToMonitor(Days=DaysToMonitor_notRunningProject)

    for f in files:
        ProjectName,_,_,_ = SplitProjectName(f)
        FullPath = os.path.join(CSVFolder, f)
        LastModificationDate = GetLastModificationDate(FullPath)
        
        logger.info(f'LastModificationDate_print: {datetime.fromtimestamp(LastModificationDate).strftime("%Y%m%d")}')

        if ProjectName not in ProjectIDs_Dict:
            logger.info(f"File {f} not in project list")
            if LastModificationDate < OneDayOld:
                os.remove(FullPath)
                logger.info(f"File is older than {DaysToMonitor_notRunningProject} day: {f} removed")
 
        stop_event.wait(timeout=24*60*60)     #24 hours waiting

    
