import pandas as pd
from datetime import datetime
from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.config.paths import MergedDuckDB
import duckdb

logger = get_configured_logger(__name__)


def get_all_data(ProjectID: str) -> pd.DataFrame:
    """
    Get all data for a project from the merged database. Used for CSV export.

    :param ProjectID: The project ID to fetch data for
    :type ProjectID: str
    :return: The project data
    :rtype: pd.DataFrame
    """
    try:
        with duckdb.connect(MergedDuckDB) as con:
            df = con.execute(
                """SELECT * FROM project_data
                WHERE ProjectID LIKE (?)
                ORDER BY DateTime ASC""",
                (ProjectID,)
            ).df()
        return df
    except Exception as e:
        logger.error(
            "project_data_fetch_failed",
            extra={"project_id": ProjectID, "error_class": type(e).__name__, "error": str(e)}, exc_info=True)
        return pd.DataFrame()

def get_project_data(ProjectID: str) -> tuple[pd.DataFrame, pd.DataFrame, str, datetime | None]:
    """
    Get both valid and error data for a project in a single query.

    Splits the project data into valid and error subsets based on date and error columns.

    :param ProjectID: Project ID to fetch
    :type ProjectID: str
    :return: tuple of (valid_data, error_data)
    :rtype: tuple[pd.DataFrame, pd.DataFrame]
    """
    try:
        with duckdb.connect(MergedDuckDB) as con:
            # Get all data for the project
            all_data = con.execute(
                """SELECT * FROM project_data
                WHERE ProjectID LIKE (?)
                ORDER BY DateTime ASC""",
                (ProjectID,)
            ).df()
        
        # Split into valid and error data in Python
        error_mask = (all_data['Date'] < '2000-01-01') | all_data['Error'].notna()
        
        valid_data: pd.DataFrame = all_data[~error_mask]
        error_data: pd.DataFrame = all_data[error_mask][['RawFileName', 'Error']]
        if not all_data.empty:
            last_row = all_data.iloc[-1]
            last_measured = last_row["RawFileName"]
            last_measured_time = last_row["DateTime"]
        else:
            last_measured, last_measured_time = "", None    
       
        
        return valid_data, error_data, last_measured, last_measured_time
    
    except Exception as e:
        logger.error(
            "project_data_query_failed",
            extra={"project_id": ProjectID, "error_class": type(e).__name__, "error": str(e)}, exc_info=True)
        
        return pd.DataFrame(), pd.DataFrame(), "", None

def get_data_freshness() -> tuple[datetime | str, int | None]:
    """Return (last_updated, net_new_rows) from meta_data, or ('', None) if unavailable."""
    try:
        with duckdb.connect(MergedDuckDB) as con:
            row = con.execute(
                """
                SELECT updated_at,
                       row_count - LAG(row_count) OVER (ORDER BY updated_at) AS new_rows
                FROM meta_data
                ORDER BY updated_at DESC
                LIMIT 1
                """
            ).fetchone()
          
        return row if row else ("", None)
    except Exception as e:
        logger.error("data_freshness_query_failed",
                     extra={"error_class": type(e).__name__, "error": str(e)}, exc_info=True)
        return "", None
