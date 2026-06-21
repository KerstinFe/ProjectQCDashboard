import os
import tempfile
from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.config.paths import internal_path
from pathlib import Path
import sqlite3
from contextlib import closing
import glob

logger = get_configured_logger(__name__)

TEMP_PREFIX = "synctmp_"
TEMP_SUFFIX = ".tmp"

def sync_database(source_db_path: str | Path | list[str] | None, dest_db_path: str | Path | list[str] | None) -> bool:
    """
    Copy database(s) from source to destination.

    Supports both single database sync and multiple database syncs.
    When lists are provided, syncs pairs of databases (first to first, second to second, etc.).

    :param source_db_path: Path(s) to the source database file(s) - can be single path or list
    :type source_db_path: str | Path | list[str] | None
    :param dest_db_path: Path(s) to the destination database file(s) - can be single path or list
    :type dest_db_path: str | Path | list[str] | None
    :return: True if all syncs were successful, False otherwise
    :rtype: bool
    """
    # Convert to lists for uniform processing
    if not source_db_path or not dest_db_path:
        logger.error(
                "database_sync_paths_missing",
                extra={"source_db_path": source_db_path, "dest_db_path": dest_db_path})
        return False
    
    if not Path(internal_path).is_dir():
        try:
            os.mkdir(internal_path)
        except Exception as e:
            logger.error("internal_dir_creation_error",
                extra={
                "internal_path": str(internal_path),
                "error_class": type(e).__name__, "error": str(e)}, exc_info=True)
   
    source_paths = [source_db_path] if not isinstance(source_db_path, list) else source_db_path
    dest_paths = [dest_db_path] if not isinstance(dest_db_path, list) else dest_db_path

    logger.debug(
            "database_sync_paths_resolved",
            extra={"source_paths": source_paths, "dest_paths": dest_paths},
        )
    
    # Validate list lengths match
    if len(source_paths) != len(dest_paths):
        logger.error(
        "database_sync_path_count_mismatch",
                extra={
                    "source_count": len(source_paths),
                    "dest_count": len(dest_paths)})
        return False
    
    all_successful = True

    for idx, (src_path, dst_path) in enumerate(zip(source_paths, dest_paths)):
        logger.debug(
                "database_sync_pair_processing",
                extra={"index": idx, "src_path": src_path, "dst_path": dst_path},
            )

            # Check if source database exists
        if not os.path.exists(src_path):
            logger.warning(
                    "database_source_not_found",
                    extra={"src_path": src_path},
                )
            all_successful = False
            continue

        fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(dst_path), prefix=TEMP_PREFIX, suffix=TEMP_SUFFIX)
        os.close(fd)

        try: 
        # Open the source read-only (mode=ro), do not remove.
        # A read-only handle makes it physically impossible for this sync to write to the
        # external instrument database, so it can never be modified or corrupted here; only
        # the temp copy is written, then swapped in atomically via os.replace below.
        # (It also avoids taking a write lock on the source if the instrument is writing it.)
            with closing(sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)) as src, \
            closing(sqlite3.connect(tmp_path)) as dst:
                with src, dst:
                    src.backup(dst)

            os.replace(tmp_path, dst_path)
            logger.info("db_sync_done", extra={"src": src_path, "dst": dst_path})
                    
        except Exception as e:
            logger.error("database_sync_failed", extra={
                "src_path": str(src_path), "dst_path": str(dst_path),
                "error_class": type(e).__name__, "error": str(e)}, exc_info=True)
            all_successful = False
        
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)     

    return all_successful 


def sweep_orphaned_temp_files(dest_paths: str | Path | list[str] | None) -> int:
    """
    Remove sync temp files orphaned by a previous run killed mid-sync.

    A normal sync either renames its temp into place (os.replace) or unlinks it on
    error, so a surviving ``synctmp_*.tmp`` can only be a crash orphan, e.g. the
    worker was SIGKILLed after the graceful-shutdown window. Called once at
    startup *before* any sync runs: nothing is writing temps yet, so every match is
    necessarily stale and safe to delete. Only safe while running Gunicorn with one worker.

    :param dest_paths: internal destination DB path(s); their containing directories 
    are swept.
    :return: number of files removed.
    """
    if not dest_paths:
        return 0

    paths = [dest_paths] if not isinstance(dest_paths, list) else dest_paths
    dirs = {os.path.dirname(str(p)) for p in paths if p}

    removed = 0
    for d in dirs:
        if not d:
            continue
        for tmp in glob.glob(os.path.join(d, f"{TEMP_PREFIX}*{TEMP_SUFFIX}")):
            try:
                os.unlink(tmp)
                removed += 1
                logger.info("orphaned_temp_removed", extra={"tmp_path": tmp})
            except FileNotFoundError:
                pass  # already gone- fine
            except OSError as e:
                logger.warning(
                    "orphaned_temp_removal_failed",
                    extra={"tmp_path": tmp, "error_class": type(e).__name__, "error": str(e)},
                )
    return removed