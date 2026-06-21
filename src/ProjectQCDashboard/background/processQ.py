from pathlib import Path
import threading
import time
from queue import Queue, Empty
from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.db.SyncDatabases import sync_database
from ProjectQCDashboard.config.paths import  external_mqqc, external_meta, Metadata_DB, MQQC_DB
from ProjectQCDashboard.db.UpdateDB import DuckDBUpdater

logger = get_configured_logger(__name__)



def process_queue(q: Queue[str|Path], stop_event: threading.Event, sync_external: bool = True,) -> None:
    """
        Process queue messages in a background thread with debounce logic.

        Listens for file system events indicating database changes, determines which database changed,
        triggers syncing of external to internal databases, and updates the merged DuckDB database.
        Runs until the stop_event is set. Handles exceptions and ensures observer cleanup on exit.

        :param q: Queue to process
        :type q:  Queue[str|Path]
        :param stop_event: Event to signal thread termination
        :type stop_event: threading.Event
    """
    DEBOUNCE_SECONDS = 5.0  # quiet period before flushing
    DuckDB = DuckDBUpdater(MQQC_DB, Metadata_DB)

    pending: set[str] = set()
    last_event_time: float | None = None

    while not stop_event.is_set():
        # Pick a timeout: short if we have pending work, long if idle.
        timeout = 0.5 if pending else 1.0

        try:
            val = q.get(timeout=timeout)
            pending.add(str(val))
            last_event_time = time.monotonic()
            logger.debug(
                "queue_item_enqueued",
                extra={"item": str(val), "pending_count": len(pending)},
            )
            continue  # go back, try to drain more
        except Empty:
            pass  # fall through to the "is it time to flush?" check

        # If we have pending events and it's been quiet long enough, flush.
        if pending and last_event_time is not None:
            quiet_for = time.monotonic() - last_event_time
            if quiet_for < DEBOUNCE_SECONDS:
                continue  # still in the quiet window, keep waiting

            # Drain any remaining events without blocking
            MAX_DRAIN = 1000
            for _ in range(MAX_DRAIN):
                try:
                    pending.add(str(q.get_nowait()))
                except Empty:
                    break

            logger.info(
                "queue_flush_started",
                extra={"pending_count": len(pending)},
            )
            try:
                # Sync each DB at most once per flush
                mqqc_set = {Path(p).resolve() for p in external_mqqc} if external_mqqc else None
                meta_path = Path(external_meta).resolve()  if external_meta else None
                synced_mqqc = False
                synced_meta = False
                if sync_external:
                    for p in pending:
                        rp = Path(p).resolve()
                        if not mqqc_set or not meta_path:
                            logger.warning(
                                "external_sync_missing_configuration",
                                extra={
                                    "mqqc_set": [str(p) for p in mqqc_set] if mqqc_set else None,
                                    "meta_path": str(meta_path) if meta_path else None,
                                },
                            )
                        elif mqqc_set and rp in mqqc_set and not synced_mqqc:
                            synced_mqqc = sync_database(external_mqqc, MQQC_DB)
                        elif meta_path and rp == meta_path and not synced_meta:
                            synced_meta = sync_database(external_meta, Metadata_DB)
                        elif rp not in mqqc_set and rp != meta_path:
                            logger.warning(f"Unknown DB file changed: {p}")

                    if synced_mqqc or synced_meta:
                        DuckDB.update_db()   
                    else:
                        logger.info("queue_flushed_no_sync_performed")     
                else:
                    DuckDB.update_db()

            except Exception as e:
                logger.error( "batch_processing_failed",extra={"error_class": type(e).__name__, "error": str(e)}, exc_info=True)
            finally:
                pending.clear()
                last_event_time = None