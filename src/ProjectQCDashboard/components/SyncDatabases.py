import os
import shutil
from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.helper.UpdateCSV import CSVUpdater
from typing import Union
from pathlib import Path

logger = get_configured_logger(__name__)

def sync_database(source_db_path: Union[str, Path], dest_db_path: Union[str, Path]) -> bool:
    """Copy database from host to container
    :param source_db_path: Path to the source database file
    :type source_db_path: Union[str, Path]
    :param dest_db_path: Path to the destination database file
    :type dest_db_path: Union[str, Path]
    :return: True if sync was successful, False otherwise
    :rtype: bool
    """
    try:
        # Check if source database exists and was recently modified
        if not os.path.exists(source_db_path):
            logger.warning(f"Source database not found: {source_db_path}")
            return False
            
        logger.info(f"Syncing database: {source_db_path} -> {dest_db_path}")
        shutil.copy2(source_db_path, dest_db_path)
        logger.info(f"Database sync completed successfully")
        return True
            
    except Exception as e:
        logger.error(f"Error during database sync: {e}")
        return False
    

class Updater_DB():
    def __init__(self, MQQC_DB: Union[str, Path], Metadata_DB: Union[str, Path]) -> None:
        """Initialize the database updater.

        :param MQQC_DB: The MQQC database
        :type MQQC_DB: Union[str, Path]
        :param Metadata_DB: The metadata database
        :type Metadata_DB: Union[str, Path]
        """
        self.MQQC_DB = MQQC_DB
        self.Metadata_DB = Metadata_DB
        self.Updater = CSVUpdater(MQQC_DB, Metadata_DB)

    def update_csv_and_db(self, val: str, external_MQQC_database: Union[str, Path], external_Meta_database: Union[str, Path]) -> None:
        """Update the CSV files and databases.

        :param val: The value indicating which database to update
        :type val: str
        :param external_MQQC_database: The external MQQC database
        :type external_MQQC_database: Union[str, Path]
        :param external_Meta_database: The external metadata database
        :type external_Meta_database: Union[str, Path]
        """
        if "MQQC" in val:
            sync_database(external_MQQC_database, self.MQQC_DB)
            logger.info("Database updated, updating csvs")
            self.Updater.update_csv()
        elif "Meta" in val:    
            sync_database(external_Meta_database, self.Metadata_DB)
            logger.info("Database updated, updating csvs")
            self.Updater.update_csv()
