import sqlite3
import re
import pandas as pd
from typing import List, Tuple, Optional, Union, Any, Dict
from datetime import datetime
from pathlib import Path
from ProjectQCDashboard.helper.common import IsStandardSample, SplitProjectName, GetLastDateToMonitor
from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.config.configuration import DaysToMonitor, PLOT_CONFIG


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


    def getProjectNamesDict(self, whichDict: str) -> Dict[str, str]:

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
                
                ProjectID, ProjectID_regex, ProjectID_regex_sql, _ = SplitProjectName(row)
                if whichDict == "regex":
                    ProjectIDs_dict.update({ProjectID: ProjectID_regex})
                if whichDict == "sql_regex":
                    ProjectIDs_dict.update({ProjectID: ProjectID_regex_sql})    

        return ProjectIDs_dict
    

    def _GetMatchingColumns(self, table_name:str = "SingleFileReport") -> List[str]:
        """
        Get a list of column names from the specified table that match the given pattern.

        :param table_name: Name of the table to query
        :type table_name: str
        :param pattern: Pattern to match column names against (SQL LIKE syntax)
        :type pattern: str
        :return: List of matching column names
        :rtype: List[str]
        """
        SQLRequest_Columns = f"SELECT * FROM {table_name} LIMIT 1;"
        PLOT_CONFIG_columns = [val[0] for val in PLOT_CONFIG.values()]
        try:
            allcols = list(query(self.metadata_db_path, SQLRequest_Columns).columns)
            # allcols = list(columns_info.columns)
            matching_columns = [col for col in allcols if col in PLOT_CONFIG_columns]
            return matching_columns
        except sqlite3.Error as e:
            logger.error(f"Error getting columns from {table_name}: {e}")
            return []
        
    def GetSQLRequest_matchingCols(self, table_name:str = "SingleFileReport" , SQLRequest:str = "normal") -> str:   
        """
        Generate a SQL SELECT statement for the specified columns.

        :param matching_columns: List of column names to include in the SELECT statement
        :type matching_columns: List[str]
        :return: SQL SELECT statement
        :rtype: str
        """    

        self.matching_columns = self._GetMatchingColumns(table_name=table_name)
        if table_name == "SingleFileReport" and "Name" not in self.matching_columns:
            self.matching_columns.insert(0, "Name")
        if table_name == "Metadata_Sample" and "SampleName_ID" not in self.matching_columns:
            self.matching_columns.insert(0,"SampleName_ID")

        matchcol_str_before = [f'"{col}"' if re.search(r'\.', col) else col for col in self.matching_columns]
        matching_columns_str = ', '.join(matchcol_str_before)
        if SQLRequest == "normal":
            return f'SELECT {matching_columns_str} FROM {table_name};'
        if SQLRequest == "ProjectID":
            return f'SELECT {matching_columns_str} FROM {table_name} WHERE ProjectID LIKE ?;'
        if SQLRequest == "Name":
            return f'SELECT {matching_columns_str} FROM {table_name} WHERE Name LIKE ? ;'


       
