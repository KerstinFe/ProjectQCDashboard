import os
import sqlite3
from pathlib import Path
from ProjectQCDashboard.config.configuration import TablesMetaData, TablesMQQCData
from ProjectQCDashboard.config.logger import get_configured_logger
from contextlib import closing

logger = get_configured_logger(__name__)


def get_table_names(db_path: str) -> list[str]:
    """
    Retrieve a list of table names from the specified SQLite database.

    :param db_path: Path to the SQLite database
    :type db_path: str
    :return: List of table names in the database
    :rtype: list[str]
    """
    try:
        # Open the source read-only (mode=ro), do not remove.
        # A read-only handle makes it physically impossible for this sync to write to the
        # external instrument database, so it can never be modified or corrupted here; only
        # the temp copy is written, then swapped in atomically via os.replace below.
        # (It also avoids taking a write lock on the source if the instrument is writing it.)
        src_uri = f"file:{db_path}?mode=ro"
        with closing(sqlite3.connect(src_uri, uri=True)) as con:
            
            with con:
                cur = con.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
                names = cur.fetchall()
                return [item for t in names for item in t] 
    
    except sqlite3.Error as e:
        logger.error("table_names_fetch_failed", extra={"db_path": db_path, 
                                                        "error_class": type(e).__name__, "error": str(e)}, exc_info=True)
        return []


def _validate_database(db_path: str, required_tables: list[str], db_type: str = "Database") -> None:
    """
    Validate that a database file exists and contains all required tables.

    Raises detailed exceptions if validation fails, including missing files or tables.

    :param db_path: Path to the database file
    :type db_path: str
    :param required_tables: List of required table names
    :type required_tables: list[str]
    :param db_type: Type/name of database for error messages
    :type db_type: str
    :raises FileNotFoundError: If the database file does not exist
    :raises ValueError: If the database is invalid or missing required tables
    """
    # Check file exists
    if not os.path.isfile(Path(db_path)):
        raise FileNotFoundError(
            f"{db_type} not found at: {db_path}\n"
            f"Please check your .env file configuration."
        )
    
    # Check tables
    try:
        table_names = get_table_names(db_path)
        logger.info(
            "database_tables_listed",
            extra={"db_type": db_type, "db_path": db_path, "table_names": table_names},
        )
        
        missing_tables = [t for t in required_tables if t not in table_names]
        
        if missing_tables:
            raise ValueError(
                f"{db_type} is missing required tables: {missing_tables}\n"
                f"Found tables: {table_names}\n"
                f"Required tables: {required_tables}\n"
                f"Database path: {db_path}"
            )
        
        logger.info("database_validated", extra={"db_type": db_type, "db_path": db_path})
        
    except sqlite3.Error as e:
        raise ValueError(
            f"Failed to read {db_type} at {db_path}\n"
            f"SQLite error: {e}\n"
            f"The file may be corrupted or not a valid SQLite database."
        )


def validate_databases(external_mqqc_dbs: list[str] | None = None, 
                      external_meta_db: str | None = None) -> None:
    """
    Validate all required databases (internal and external, if provided).

    Checks that all specified databases exist and contain the required tables. Raises exceptions if any are missing or invalid.

    :param external_mqqc_dbs: List of paths to external MQQC databases
    :type external_mqqc_dbs: list[str] | None
    :param external_meta_db: Path to external metadata database
    :type external_meta_db: str | None
    :raises FileNotFoundError: If any required database is missing
    :raises ValueError: If any database is invalid or missing tables
    """
    logger.info("database_validation_started")
    if not external_mqqc_dbs:
        external_mqqc_dbs = []
    elif not isinstance(external_mqqc_dbs, list):
        external_mqqc_dbs = [external_mqqc_dbs]
   
    # Validate external databases if provided (in container)
    if external_mqqc_dbs:
        for i, db_path in enumerate(external_mqqc_dbs, 1):
            _validate_database(db_path, TablesMQQCData, f"External MQQC Database #{i}")
    
    if external_meta_db:
        _validate_database(external_meta_db, TablesMetaData, "External Metadata Database")
    
    
    logger.info("external_databases_validated")
