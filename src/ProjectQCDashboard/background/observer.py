from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from queue import Queue
import threading
from typing import Any
from ProjectQCDashboard.config.configuration import PollingIntervalSeconds
from ProjectQCDashboard.config.paths import DB_Paths_towatch,external_mqqc, external_meta

from ProjectQCDashboard.config.logger import get_configured_logger

logger = get_configured_logger(__name__)
# q = Queue()





class myHandler(FileSystemEventHandler):
    def __init__(self, q: Queue[Path | str],  watched_files: list[str]) -> None:
        """
        Initialize the file system event handler for database observation.

        This handler writes relevant file system events to a queue and signals when a database was updated.

        :param q: The queue to put events into
        :type q: Queue[Path | str]
        """
        super().__init__()
        self.q = q
       
        # Combine all databases to watch
        self.DB = watched_files

    def _enqueue_if_watched(self, event: Any) -> None:
        """
        Function to queue the watched event.

        :param event: The file system event
        :type event: Any
        :return: None
        :rtype: None
        """
        WatchedEvent = Path(event.src_path).as_posix()
        logger.debug("watched_event_observed", extra={"path": WatchedEvent})
        if WatchedEvent in self.DB:
            logger.info("watched_event_queued", extra={"path": WatchedEvent})
            self.q.put(WatchedEvent)

    def on_modified(self, event: Any) -> None:
        self._enqueue_if_watched(event)

    def on_created(self, event: Any) -> None:
        self._enqueue_if_watched(event)
            
    def on_any_event(self, event: Any) -> None:
        """
        Log any file system event for debugging purposes.

        :param event: The file system event
        :type event: Any
        :return: None
        :rtype: None
        """
        logger.debug(
            "filesystem_event_received",
            extra={"event_type": event.event_type, "path": event.src_path},
        )

    
           

class Observer_DBs():
    def __init__(self,  q: Queue[Path | str]) -> None:
        """
        Initialize the Observer_DBs class to manage database observers.

        Sets up the list of directories to watch and prepares the observer list.

        :param q: The queue to put events into
        :type q: Queue[Path | str]

        """
        self.DB_Paths_towatch = [str(DB) for DB in DB_Paths_towatch]
        self.DB_Paths_towatch = list(set(self.DB_Paths_towatch))
        self.Observer_list: list[PollingObserver] = []
        self.q = q

    def start_observing(self, stop_event: threading.Event) -> None:
        """
        Start observing the configured database directories for changes.

        This method runs until the stop_event is set, then closes all observers.

        :param stop_event: Event to signal stopping the observation
        :type stop_event: threading.Event
        :return: None
        :rtype: None
        """

        logger.info("observer_starting", extra={"directories": self.DB_Paths_towatch})
        
        watched_files = [Path(db).as_posix() for db in (external_mqqc + [external_meta])]
        handler = myHandler(self.q, watched_files)
       
        if len(self.DB_Paths_towatch) >= 1:

            for idx, watch_dir in enumerate(self.DB_Paths_towatch, 1):
                try:
                    observer = start_observer(handler, watch_dir)
                    self.Observer_list.append(observer)
                    logger.info(
                        "observer_started",
                        extra={"observer_index": idx, "directory": watch_dir},
                    )
                except Exception as e:
                    logger.error(
                        "observer_start_failed",
                        extra={"observer_index": idx, "directory": watch_dir,
                               "error_class": type(e).__name__, "error": str(e)}, exc_info=True)

        else:
            logger.error(
                "observer_no_directories",
                extra={
                    "count_db_towatch": len(self.DB_Paths_towatch),
                    "directories": self.DB_Paths_towatch})
            
        if len(self.Observer_list) == 0:
            logger.error("no_observer_started",
                extra={"length observerlist": len(self.Observer_list)})
        
        while not stop_event.is_set():
            stop_event.wait(timeout=1)
        
        self.close_observations()

    def close_observations(self) -> None:
        """
        Stop all active observers and clean up resources.

        :return: None
        :rtype: None
        """
        logger.info("observer_stopping", extra={"count": len(self.Observer_list)})
        
        for i, observer in enumerate(self.Observer_list, 1):
            if observer and observer.is_alive():
                try:
                    observer.stop()
                    observer.join()
                    logger.info("observer_stopped", extra={"observer_index": i})
                except Exception as e:
                    logger.error("observer_stop_failed", extra={"observer_index": i, 
                                                        "error_class": type(e).__name__, "error": str(e)}, exc_info=True)

def start_observer(handler: Any, watch_dir: str) -> PollingObserver:
    """
    Start a PollingObserver for the specified directory and handler.

    :param handler: The event handler for file system events
    :type handler: Any
    :param watch_dir: The directory path to watch
    :type watch_dir: str
    :return: The started PollingObserver instance
    :rtype: PollingObserver
    """
    # Set polling interval to 60 seconds (default is 1 second), Polling Observer is more robust on network drives
    observer = PollingObserver(timeout=PollingIntervalSeconds)
    observer.schedule(handler, path=watch_dir, recursive=False)
    observer.start()

    logger.info(
        "directory_watch_started",
        extra={"directory": watch_dir, "polling_interval_seconds": PollingIntervalSeconds},
    )
    return observer

                 
