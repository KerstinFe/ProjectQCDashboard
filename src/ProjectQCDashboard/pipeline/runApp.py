import time
from dash import Dash
from queue import Queue
import threading
from pathlib import Path
from ProjectQCDashboard.db.UpdateDB import DuckDBUpdater
from ProjectQCDashboard.ui.AppLayout import AppLayout
from ProjectQCDashboard.db.SyncDatabases import sync_database, sweep_orphaned_temp_files
from ProjectQCDashboard.db.ValidateDatabases import validate_databases
from ProjectQCDashboard.background.observer import Observer_DBs
from ProjectQCDashboard.config.RunningContainer import _is_running_in_container
from ProjectQCDashboard.config.paths import  external_mqqc, external_meta, Metadata_DB, MQQC_DB
from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.background.processQ import process_queue

logger = get_configured_logger(__name__)


def create_app() -> Dash:
    """
    Create and configure the Dash application for containerized (production) deployment.

    This function performs the following steps:
    1. Validates that the application is running in a container
    2. Verifies database files exist
    3. Syncs external databases to internal copies
    4. Creates/updates the merged DuckDB database
    5. Sets up file system observers for database changes
    6. Initializes background threads for monitoring database changes
    7. Creates and returns the Dash application instance

    :return: Configured Dash application instance
    :rtype: Dash
    :raises RuntimeError: If not running in a container or initialization fails
    """

    # Debug container detection
    logger.info(
            "container_detection_checked",
            extra={"is_running_in_container": _is_running_in_container()},
        )
    
    logger.debug(
            "external_db_paths",
            extra={"external_mqqc": external_mqqc, "external_meta": external_meta},
        )
    

    
    app_layout_instance = AppLayout()
       
    if not external_mqqc:
        # Local dev mode without observer — validate internal DBs directly
        validate_databases(MQQC_DB, Metadata_DB)
    else:
        # Container mode or local dev with observer configured
        validate_databases(external_mqqc, external_meta) # checks whether the DBs exist in the container or in other folder for local mode
        sweep_orphaned_temp_files([*MQQC_DB, Metadata_DB])
        synced_mqqc = sync_database(external_mqqc, MQQC_DB) # sync the external DBs to the internal ones
        synced_meta = sync_database(external_meta, Metadata_DB)

        if not synced_mqqc or not synced_meta:
            logger.error("database_synchronization failed", 
                         extra = {"synced_mqqc": synced_mqqc, "synced_meta": synced_meta})
            raise RuntimeError("Databases not were not synchronized.")

    q: Queue[Path | str] = Queue()
    
    logger.info("database_initialization_started")
    try:
        DuckDB = DuckDBUpdater(MQQC_DB, Metadata_DB)
        DuckDB.update_db(force_full_refresh=True)
        logger.info("database_updated")
    except Exception as e:
        logger.error(
            "database_initialization_failed",
            extra={"error_class": type(e).__name__, "error": str(e)}, exc_info=True)
        raise RuntimeError("Database initialization failed") from e
    

    # Cooperative stop signal for the observer and queue threads (used only as a loop guard).
    # Intentionally never set: both threads are daemons, so process teardown stops them.
    # That is safe because the sync uses a read-only source plus an atomic os.replace,
    # and the DuckDB merge is transactional (an interrupted merge rolls back on next open).
    # Registering a signal handler here would override Gunicorn's own worker
    # handlers and break its graceful shutdown, so I deliberately rely on daemon teardown.
    # Set this only from the local __main__ path if you want cooperative shutdown during dev.

    stop_event = threading.Event()

    if external_mqqc:
        # Watch the mounted external files (the actual mount points)
        try:
            Observer = Observer_DBs(q)
        except Exception as e:
            logger.error(
                "observer_initialization_failed",
                extra={"error_class": type(e).__name__, "error": str(e)}, exc_info=True)
            
            raise RuntimeError("Observer initialization failed") from e
    
        # background thread to watch for external DB changes
        background_thread_DB = threading.Thread(target=Observer.start_observing, args=(stop_event,))
        background_thread_DB.daemon = True
        background_thread_DB.start()

        # For production (Gunicorn), queue processing runs in background thread
        sync_external = True
        queue_thread = threading.Thread(target=process_queue, args=(q, stop_event,sync_external,))
        queue_thread.daemon = True
        queue_thread.start()

    else:
        logger.info("no_external_dbs_defined_observer_not_started") 

    app = app_layout_instance.createapp()
    logger.info("dashboard_started")       
   
    return app


if __name__ == '__main__':  
    app = create_app()
    app.run(debug=False, host='127.0.0.1', port=8050)





