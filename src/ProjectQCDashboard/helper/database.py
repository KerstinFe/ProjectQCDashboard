import sqlite3
import pandas as pd
from typing import List, Tuple, Optional, Union, Any, Dict
from datetime import datetime, timedelta
import re
import time
from pathlib import Path
from ProjectQCDashboard.helper.common import convert_timestamps, IsStandardSample, SplitProjectName, GetLastDateToMonitor
from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.config.configuration import DaysToMonitor


logger = get_configured_logger(__name__)
def query(FileToWatch: Union[str, Path], SQLRequest: str, params: Optional[Tuple] = None) -> Any:
    """Execute a SQL query on a SQLite database.

    :param FileToWatch: Path to the SQLite database file
    :type FileToWatch: Union[str, Path]
    :param SQLRequest: SQL query to execute
    :type SQLRequest: str
    :param params: Query parameters, defaults to None
    :type params: Optional[Tuple], optional
    :return: Query result
    :rtype: Any
    """
    with sqlite3.connect(FileToWatch) as con:

        return pd.read_sql_query(SQLRequest, con, params=params)
        
def GetTableNames(DB: str) -> List[str]:

    """Get a list of table names from the database.

    :return: List of table names
    :rtype: List[str]
    """
    
    try:
        with sqlite3.connect(DB) as con:
            cur = con.cursor()
            names = cur.execute('''SELECT name FROM sqlite_master WHERE type='table';''')
            names = cur.fetchall()
            return [item for t in names for item in t]
    except sqlite3.Error as e:
        logger.error(f"Error getting table names: {e}")
        return []
    

class Database_Call:
    def __init__(self, metadata_db_path: Union[str, Path]) -> None:

        """
        Initialize the database call with the metadata database path.

        :param metadata_db_path: Path to the metadata SQLite database file
        :type metadata_db_path: Union[str, Path]
        """


        self.metadata_db_path = metadata_db_path
        self.SQLRequest_ProjectNames = '''SELECT ProjectID 
                        FROM Metadata_Sample
                        WHERE datetime(CreationDate) > ?;'''  


    def getProjectNamesDict(self) -> Dict[str, str]:

        """
        Get a dictionary of project names and their regex patterns.
        
        :return: Dictionary of project names and their regex patterns
        :rtype: Dict[str, str]
        """

        lastDate= GetLastDateToMonitor(Days=DaysToMonitor)
        converted = datetime.fromtimestamp(lastDate).strftime("%Y-%m-%d %H:%M:%S.000")
        AllProjectNames =  query(self.metadata_db_path, self.SQLRequest_ProjectNames, params=(converted,))
        AllProjectNames = list(set(AllProjectNames["ProjectID"].to_list()))

        ProjectIDs_dict = {}
        for row in AllProjectNames:
            if not IsStandardSample(row):
                ProjectID, ProjectID_regex, _, _ = SplitProjectName(row)
                ProjectIDs_dict.update({ProjectID: ProjectID_regex})

        return ProjectIDs_dict

    def getProjectNamesDict_SqlRegex(self) -> Dict[str, str]:

        """
        Get a dictionary of project names and their regex patterns using SQL regex.
        :return: Dictionary of project names and their regex patterns
        :rtype: Dict[str, str]

        """

        lastDate = GetLastDateToMonitor(Days=DaysToMonitor)

        converted = datetime.fromtimestamp(lastDate).strftime("%Y-%m-%d %H:%M:%S.000")

        AllProjectNames =  query(self.metadata_db_path, self.SQLRequest_ProjectNames, params=(converted,))
        AllProjectNames = list(set(AllProjectNames["ProjectID"].to_list()))

        ProjectIDs_dict = {}
        for row in AllProjectNames:
            if not IsStandardSample(row):
                ProjectID, _, ProjectID_regex_sql, _ = SplitProjectName(row)
                ProjectIDs_dict.update({ProjectID: ProjectID_regex_sql})

        return ProjectIDs_dict




       
