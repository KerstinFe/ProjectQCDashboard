import os
from watchdog.observers.polling import PollingObserver
from watchdog.events import LoggingEventHandler
from pathlib import Path
from queue import Queue
from typing import Any, Union
q = Queue()
from ProjectQCDashboard.config.configuration import PollingIntervalSeconds
from ProjectQCDashboard.config.logger import get_configured_logger

logger = get_configured_logger(__name__)

class myHandler(LoggingEventHandler):
    def __init__(self, q: Any, DB: Any) -> None:
        """Handle file system events. write events to a queue.

        :param q: The queue to put events into
        :type q: Any
        :param DB: The database path to watch
        :type DB: Any
        :return: None
        :rtype: None
        """
        super().__init__()
        self.q = q
        self.DB = DB

    def on_modified(self, event: Any) -> None:
        """Handle modified events.
        :param event: The file system event
        :type event: Any
        :return: None
        :rtype: None
        """

        WatchedEvent = Path(event.src_path).as_posix()
      
        if WatchedEvent == self.DB:
            self.q.put(WatchedEvent)  # Put the actual event path, not undefined 'x'

class Observer_DBs():
    def __init__(self, MQQC_DB: Union[str, Path], Metadata_DB:  Union[str, Path]) -> None:
        """Initialize the database observers.
        :param MQQC_DB: The MQQC database path to watch
        :type MQQC_DB: Union[str, Path]
        :param Metadata_DB: The metadata database path to watch
        :type Metadata_DB: Union[str, Path]
        :return: None
        :rtype: None
        """
        self.MQQC_DB = MQQC_DB
        self.Metadata_DB = Metadata_DB
        self.Observer_MQQC = None
        self.Observer_Meta = None

    def start_observing(self, stop_event: Any) -> None:
        """Start observing the databases for changes.
        :param stop_event: Event to signal stopping the observation
        :type stop_event: Any
        :return: None
        :rtype: None
        """

        logger.info(f"Starting to watch external databases {self.MQQC_DB}, {self.Metadata_DB} for changes")
        self.Observer_MQQC = start_observer(q, self.MQQC_DB)
        self.Observer_Meta = start_observer(q, self.Metadata_DB)
        
        # Log observer status
        if self.Observer_MQQC:
            logger.info("Successfully started external MQQC database observer")
        else:
            logger.warning("Failed to start external MQQC database observer")
            
        if self.Observer_Meta:
            logger.info("Successfully started external Metadata database observer")
        else:
            logger.warning("Failed to start external Metadata database observer")
        
        while not stop_event.is_set():
            stop_event.wait(timeout=1)  # Check every second
        # Clean up when stopping
        self.ClosingObservations()

    def ClosingObservations(self) -> None:
        """Stop observing the databases.
        :return: None
        :rtype: None
        """

        if self.Observer_MQQC and self.Observer_MQQC.is_alive():
            self.Observer_MQQC.stop()
            self.Observer_MQQC.join()
        if self.Observer_Meta and self.Observer_Meta.is_alive():
            self.Observer_Meta.stop()
            self.Observer_Meta.join()

def start_observer(q: Any, DB: Union[str, Path]) -> Any:
    """Start an observer for the specified database.
    :param q: The queue to put events into
    :type q: Any
    :param DB: The database path to watch
    :type DB: Union[str, Path]
    :return: The observer instance
    :rtype: Any
    """

    
    path_to_watch = os.path.dirname(DB)
    if not path_to_watch:  # If dirname returns empty (for files in root), watch root
        path_to_watch = "/"
    
    handler = myHandler(q, DB)
    # Set polling interval to 60 seconds (default is 1 second), Polling Observer is more robust on network drives
    observer = PollingObserver(timeout=PollingIntervalSeconds)
    observer.schedule(handler, path=path_to_watch, recursive=False)
    observer.start()

    logger.info("Watching directory: %s for changes to %s (using polling every %d seconds)", path_to_watch, DB, PollingIntervalSeconds)
    return observer

                 
