from datetime import date, datetime
import  os
import re
import sys
import sqlite3
from typing import Tuple, List
from pathlib import Path
import dateutil.relativedelta
import pandas as pd
from datetime import timedelta
from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.config.paths import CSVFolder
from typing import Any, Dict, List, Optional, Union

logger = get_configured_logger(__name__)

def MakePathNice(PathToMakeNice: str) -> str:
    """Clean and normalize file path.
    :param PathToMakeNice: The file path to clean
    :type PathToMakeNice: str
    :return: Cleaned and normalized file path
    :rtype: str

    """
    PathToMakeNice = PathToMakeNice.replace('"', '')
    PathToMakeNice = PathToMakeNice.replace("'", "")
    PathToMakeNice = Path(PathToMakeNice).as_posix()

    return PathToMakeNice


def SplitProjectName(Name: str) -> Tuple[str, str, str, str]:
    """Split project name into components.
    
    :param Name: The project name
    :type Name: str
    :return: Tuple of (ProjectID, ProjectID_regex, ProjectID_regex_sql, ProjectID_Date)
    :rtype: Tuple[str, str, str, str]
    """

    Name = os.path.splitext(Name)[0]
    Name = os.path.basename(Name)
    Names_splitted = Name.split("_")
    ProjectID = (Names_splitted[0]+"_"+Names_splitted[1]+"_"+Names_splitted[2])
    ProjectID_regex = (Names_splitted[0]+"_"+re.sub("[0-9]{2}$", "[0-9]{2}", Names_splitted[1])+"_"+Names_splitted[2])
    ProjectID_regex_sql =(Names_splitted[0]+"_"+re.sub("[0-9]{2}$", "__", Names_splitted[1])+"_"+Names_splitted[2]+ "%")
    ProjectID_Date = Names_splitted[1]
    
    return ProjectID, ProjectID_regex, ProjectID_regex_sql, ProjectID_Date

def IsStandardSample(Name: str) -> bool:
    """Check if the project name is a standard sample.
    
    :param Name: The project name
    :type Name: str
    :return: True if standard sample, False otherwise   
    :rtype: bool
    """
    

    return bool(re.search("HSstd", Name)) or bool(re.search("[Ss]tandar[dt]", Name))

def GetLastDateToMonitor(Days: int) -> Any:
    """Get the last date to monitor based on the number of days.
    :param Days: Number of days to look back
    :type Days: int
    :return: Timestamp of the last date to monitor
    :rtype: Any
    """


    currentDate = datetime.today()
    lastDate = currentDate-timedelta(days=Days)
    lastDate = datetime.timestamp(lastDate)
    return lastDate


def removeLastNumber_fromFileName(Name: str) -> Any:
    """Remove the last number from the file name.

    :param Name: The original file name
    :type Name: str
    :return: The modified file name
    :rtype: Any
    """
    NewFileName = Name.split("_")
    NewFileName.pop()
    NewFileName ="_".join(NewFileName)
    return NewFileName

def convert_timestamps(timestamp: Any) -> Any:
    """Convert timestamp to date, time, and datetime strings.
    
    :param timestamp: The input timestamp (various formats)
    :type timestamp: Any
    :return: Tuple of (date_str, time_str, datetime_str)
    :rtype: Any
    """
    

    try:
        # Handle None or empty values
        if timestamp is None or timestamp == '' or pd.isna(timestamp):
            logger.warning(f"Received None/empty timestamp, using default values")
            return "1900.01.01", "00:00:00", "1900-01-01T00:00:00"
            
        # Convert to pandas datetime, handling various formats
        dt = pd.to_datetime(timestamp)
        
        
        # Extract the components as strings
        date_str = dt.strftime("%Y.%m.%d")           # e.g., "2025.01.03"
        time_str = dt.strftime("%H:%M:%S")           # e.g., "11:44:38"
        datetime_str = dt.strftime("%Y-%m-%dT%H:%M:%S")  # e.g., "2025-01-03T11:44:38"
        
        return date_str, time_str, datetime_str
        
    except Exception as e:
        logger.error(f"Error converting timestamp '{timestamp}': {e}")
        # Return default values if conversion fails
        return "1900.01.01", "00:00:00", "1900-01-01T00:00:00"

def GetLastModificationDate(file: Union[str, Path]) -> Any:
    """Get the last modification date of a file.
    :param file: The file path
    :type file: Union[str, Path]
    :return: The last modification date
    :rtype: Any
    """
    return os.path.getmtime(file)

def CreateOutputFilePath(ProjectID: Any) -> Any:
    '''Create output file path based on input file.
    :param ProjectID: The project ID
    :type ProjectID: Any
    :return: The output file path
    :rtype: Any
    '''
    FileName = "".join((ProjectID,'_ProjectData.csv'))
    OutputFilePath =  os.path.join(CSVFolder, FileName)
 
    return OutputFilePath

