# import pandas as pd
import os
import sys
# import re
import time
import sqlite3
from pathlib import Path
from ProjectQCDashboard.helper.UpdateCSV import CSVUpdater
from ProjectQCDashboard.components.AppLayout import AppLayout
from ProjectQCDashboard.components.SyncDatabases import sync_database
from ProjectQCDashboard.config.paths import csvFiles_Folder
from ProjectQCDashboard.helper.CleanTempCsv import CleanUp_csvFiles
from ProjectQCDashboard.components.UserInput import DB_In_Container, get_UserInput
from ProjectQCDashboard.helper.observer import Observer_DBs, q
from ProjectQCDashboard.helper.RunningContainer import _is_running_in_container
from ProjectQCDashboard.components.SyncDatabases import Updater_DB
from ProjectQCDashboard.config.paths import external_mqqc, external_meta, Metadata_DB, \
                                    MQQC_DB, external_MQQC_path, external_Meta_path
from typing import Any, Dict, List, Optional, Union

from queue import Queue, Empty
import threading
from ProjectQCDashboard.config.logger import get_configured_logger

logger = get_configured_logger(__name__)

    
def create_app() -> Any:
    """Create and configure the Dash application with background threads"""

    # Debug container detection
    logger.info(f"Container detection debug:")
    logger.info(f"  /.dockerenv exists: {os.path.exists('/.dockerenv')}")
    logger.info(f"  sys.stdin.isatty(): {sys.stdin.isatty()}")
    logger.info(f"  _is_running_in_container(): {_is_running_in_container()}")
    logger.info(f"Environment: { os.environ}")
    
    if not _is_running_in_container():
        logger.error("This script is designed to run only in containers. Use runApp_local for local development.")
        raise RuntimeError("Container-only script executed outside container")

    # Import container-specific variables after container check
    

    DB_In_Container(external_mqqc, external_meta)
    sync_database(external_mqqc, MQQC_DB)
    sync_database(external_meta, Metadata_DB)


    logger.info("Initial updating/creation of csv files")
    CSVUpdater(MQQC_DB, Metadata_DB).FirstCreationOfCsvs()
    
    Updater = Updater_DB(MQQC_DB, Metadata_DB)
    # Watch the mounted external files (the actual mount points)
    Observer = Observer_DBs(external_mqqc, external_meta)
    time.sleep(2)
    
    # Start background threads
    stop_event = threading.Event()
  
    background_thread_DB = threading.Thread(target=Observer.start_observing, args=(stop_event,))
    background_thread_DB.daemon = True
    background_thread_DB.start()

    deletingcsvFiles_thread = threading.Thread(target=CleanUp_csvFiles, args=(csvFiles_Folder, Metadata_DB,stop_event))
    deletingcsvFiles_thread.daemon = True
    deletingcsvFiles_thread.start()

    logger.info("Csvs created/updated, now starting Dashboard")
    app = AppLayout(MQQC_DB, Metadata_DB).CreateApp()
    logger.info("Dashboard started")
    # For production (Gunicorn), queue processing runs in background thread
    def process_queue(stop_event: Any) -> None:
        """Process queue messages in background thread"""
        try:
            while not stop_event.is_set():
                try:
                    val = q.get(timeout=1)
                    logger.info(f"External database change detected: {val}")
                    
                    # Determine which database changed and sync it
                    if "external_MQQC_database" in val:
                        logger.info("External MQQC database changed, syncing to internal database")
                        Updater.update_csv_and_db("MQQC", external_mqqc, external_meta)
                    elif "external_Meta_database" in val:
                        logger.info("External Metadata database changed, syncing to internal database") 
                        Updater.update_csv_and_db("Meta", external_mqqc, external_meta)
                    else:
                        logger.warning(f"Unknown database file changed: {val}")

                except Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error processing queue: {e}")
        except KeyboardInterrupt:
            logger.info("Queue processing interrupted")
            stop_event.set()
            Observer.ClosingObservations()
            logger.info("Observer closed")

    # Start queue processing thread for production
    queue_thread = threading.Thread(target=process_queue, args=(stop_event,))
    queue_thread.daemon = True
    queue_thread.start()
    
    return app

# Create app instance for Gunicorn
app = create_app()
if __name__ == '__main__':  
    server = app.run_server(host='0.0.0.0', port=8000)





