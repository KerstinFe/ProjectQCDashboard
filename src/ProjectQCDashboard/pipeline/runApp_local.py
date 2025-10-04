import time
from ProjectQCDashboard.helper.UpdateCSV import CSVUpdater
from ProjectQCDashboard.components.AppLayout import AppLayout
from ProjectQCDashboard.config.paths import CSVFolder
from ProjectQCDashboard.helper.CleanTempCsv import CleanUp_csvFiles
from ProjectQCDashboard.components.UserInput import  get_UserInput
from ProjectQCDashboard.helper.observer import q, Observer_DBs
from ProjectQCDashboard.helper.RunningContainer import _is_running_in_container
from queue import Empty
import threading
from ProjectQCDashboard.config.logger import get_configured_logger
from typing import Any

logger = get_configured_logger(__name__)

    
def create_app() -> Any:
    """Create and configure the Dash application with background threads"""

    if _is_running_in_container():
         raise RuntimeError("Outside Container script executed inside container")
       
    Metadata_DB, MQQC_DB = get_UserInput()
  
    logger.info("Initial updating/creation of csv files")
    Updater = CSVUpdater(MQQC_DB, Metadata_DB)
    Updater.FirstCreationOfCsvs()
    time.sleep(2)
    
    # Start background threads
    stop_event = threading.Event()
    
    # Use Observer_DBs class like the container version
    Observer = Observer_DBs(MQQC_DB, Metadata_DB)
    background_thread_DB = threading.Thread(target=Observer.start_observing, args=(stop_event,))
    background_thread_DB.daemon = True
    background_thread_DB.start()

    deletingcsvFiles_thread = threading.Thread(target=CleanUp_csvFiles, args=(CSVFolder, Metadata_DB,stop_event))
    deletingcsvFiles_thread.daemon = True
    deletingcsvFiles_thread.start()

    logger.info("Csvs created/updated, now starting Dashboard")
    app = AppLayout(Metadata_DB).CreateApp()
    logger.info("Dashboard started")
    # For production (Gunicorn), queue processing runs in background thread
    def process_queue(stop_event: Any) -> None:
        """Process queue messages in background thread
        :param stop_event: Event to signal stopping the processing
        :type stop_event: Any
        :return: None
        :rtype: None
        """
        try:
            while not stop_event.is_set():
                try:
                    val = q.get(block=False, timeout=1)
                    
                    if "MQQC" in val:
                        logger.info("Database updated, updating csvs")
                        Updater.update_csv()
                    elif "Meta" in val: 
                        logger.info("Database updated, updating csvs")
                        Updater.update_csv()
                except Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error processing queue: {e}")
        except KeyboardInterrupt:
            logger.info("Queue processing interrupted")
            stop_event.set()
            background_thread_DB.join(timeout=2)
            deletingcsvFiles_thread.join(timeout=2)

    # Start queue processing thread for production
    queue_thread = threading.Thread(target=process_queue, args=(stop_event,))
    queue_thread.daemon = True
    queue_thread.start()
    
    return app

# Create app instance for Gunicorn
app = create_app()
server = app.server
if __name__ == "__main__":
    # For local development, we handle things slightly differently
    logger.info("Running in development mode")
    
    # Get the app (already created above with background threads)
    # But for development, we need to run it and handle the main queue loop
    logger.info("Dashboard starting...")
    app.run(debug=False, host='0.0.0.0', port=8050)




