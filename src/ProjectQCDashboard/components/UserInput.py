import os
from pathlib import Path
from typing import Tuple, Union, List
import sqlite3
from ProjectQCDashboard.config.configuration import  TablesMetaData, TablesMQQCData
from ProjectQCDashboard.config.paths import DEFAULT_METADATA_DB, DEFAULT_MQQC_DB
from ProjectQCDashboard.helper.common import MakePathNice
from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.helper.RunningContainer import _is_running_in_container

logger = get_configured_logger(__name__)


def _validate_database_tables(db_path: str, Tables: list) -> bool:
    '''Check if database has required tables.
    :param db_path: Path to the database file
    :type db_path: str
    :param Tables: Set of required table names
    :type Tables: list
    :return: True if all required tables are present, False otherwise
    :rtype: bool
    '''
    try:
        table_names = GetTableNames(db_path)
        logger.info(f"Tables in {db_path}: {table_names}")

        # Ensure that all required tables are present in the database.
        # Accept extra tables in the database (i.e. database can contain more tables than required).
        missing = [t for t in Tables if t not in table_names]
        if not missing:
            return True
        else:
            logger.info(f"Missing required tables in {db_path}: {missing}")
            return False
    except Exception as e:
        logger.error(f"Error validating database tables: {e}")
        return False



def _validate_database_path(db_path: str, Tables: list) -> bool:
    '''Validate database path and handle creation if needed.
    :param db_path: Path to the database file
    :type db_path: str
    :param Tables: Set of required table names
    :type Tables: list
    :return: True if database is valid, False otherwise
    :rtype: bool
    '''
    if os.path.isdir(db_path):
        logger.info("Provided path is a directory not a file. Please reenter filename")
        return False
        
    if not Path(db_path).suffix == ".sqlite":
        logger.info("Provided file is not a .sqlite db. Please try again.")
        return False
    
    if os.path.isfile(db_path):
        logger.info(f"SQL DB for Metadata defined as: {db_path}")
        
        if _validate_database_tables(db_path,Tables):
            logger.info("DB with tables exists")
            return True
        else:
            logger.info(f'{db_path} exists, but does not contain required tables.')
            return False
    else:
        logger.info(f'{db_path} does not exist.')
        return False
    
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

def get_UserInput_Fun(defaultdb: str, Tables: list) -> str:
    """Function to get the location of the DB file when starting the script.
    In container environments, automatically uses defaults if valid.
    :param defaultdb: Default database path to use in container
    :type defaultdb: str
    :param Tables: List of required table names
    :type Tables: list
    :return: Validated database path
    :rtype: str
    """
    # If running in container, try to use defaults automatically
    if _is_running_in_container():
        logger.info(f"Container environment detected, attempting to use default: {defaultdb}")
        if os.path.isfile(defaultdb) and _validate_database_tables(defaultdb, Tables):
            logger.info(f"Using default database: {defaultdb}")
            return defaultdb
        else:
            logger.error(f"Default database {defaultdb} not found or invalid in container")
            raise FileNotFoundError(f"Required database {defaultdb} not found in container")
    
    # Interactive mode for development
    use_default_db = input(f'If {defaultdb} is correct location of Metadata press enter, else enter False.')
    
    if use_default_db == '':
        DB = defaultdb
        logger.info(f'{DB} is file? : {os.path.isfile(DB)}')
        
        if os.path.isfile(DB):
            if not _validate_database_tables(DB, Tables):
                logger.info(f'{DB} exists, but does not contain required tables.')
                use_default_db = 'False'  # Force manual input
                 
            else:
                logger.info("DB with tables exists")
        else:
            use_default_db = 'False'  # Force manual input

    # Manual database path input
    if use_default_db != '':
        DB = ''
        
        while not _validate_database_path(DB, Tables):
            DB = input("Set location of SQL Database for Metadata: ")
            DB = MakePathNice(DB)

    return DB        

def get_UserInput(DEFAULT_METADATA_DB: Union[str, Path] = DEFAULT_METADATA_DB, 
                  DEFAULT_MQQC_DB: Union[str, Path] = DEFAULT_MQQC_DB) -> Tuple[str, str]:
    
    ''' Function to get the location of the metadata file and MQQC DB file when starting the script.
    :param DEFAULT_METADATA_DB: Default path for the metadata database
    :type DEFAULT_METADATA_DB: Union[str, Path]
    :param DEFAULT_MQQC_DB: Default path for the MQQC database
    :type DEFAULT_MQQC_DB: Union[str, Path]
    :return: Tuple containing paths to the metadata and MQQC databases
    :rtype: Tuple[str, str]

    '''
    
    # Handle Metadata Database Input
    metadata_db = get_UserInput_Fun(DEFAULT_METADATA_DB, TablesMetaData)
    mqqc_db = get_UserInput_Fun(DEFAULT_MQQC_DB, TablesMQQCData)
    
    return metadata_db, mqqc_db

def DB_In_Container(external_mqqc: str, external_meta: str) -> bool:
    """Function to validate database files in container environment.
    Maps default paths to external mounted database paths.
    :param external_mqqc: Path to the external MQQC database
    :type external_mqqc: str
    :param external_meta: Path to the external Metadata database
    :type external_meta: str
    :return: True if both databases are valid, False otherwise
    :rtype: bool

    """
    logger.info(f"Validating external databases...")
    logger.info(f"  MQQC path: {external_mqqc}")
    logger.info(f"  Meta path: {external_meta}")
    
    # Validate MQQC database
    if os.path.isfile(external_mqqc) and _validate_database_tables(external_mqqc, TablesMQQCData):
        logger.info(f"Using external MQQC database: {external_mqqc}")
        db1 = True
    else:
        logger.error(f"External MQQC database {external_mqqc} not found or invalid")
        logger.info(f"File exists: {os.path.isfile(external_mqqc)}")
        if os.path.isfile(external_mqqc):
            logger.info(f"File exists but tables invalid. Expected tables: {TablesMQQCData}")
            table_names = GetTableNames(external_mqqc)
            logger.info(f"Tables in {external_mqqc}: {table_names}")
        raise FileNotFoundError(f"Required external MQQC database {external_mqqc} not found in container")

    # Validate Metadata database
    if os.path.isfile(external_meta) and _validate_database_tables(external_meta, TablesMetaData):
        logger.info(f"Using external Metadata database: {external_meta}")
        db2 = True
    else:
        logger.error(f"External Metadata database {external_meta} not found or invalid")
        logger.info(f"File exists: {os.path.isfile(external_meta)}")
        if os.path.isfile(external_meta):
            table_names = GetTableNames(external_meta)
            logger.info(f"Tables in {external_meta}: {table_names}")
            logger.info(f"File exists but tables invalid. Expected tables: {TablesMetaData}")
        raise FileNotFoundError(f"Required external Metadata database {external_meta} not found in container")

    return True if db1 and db2 else False

       