from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.config.paths import  MergedDuckDB
import threading
import duckdb

logger = get_configured_logger(__name__)

_state_lock = threading.Lock()

# cache of the version of cache and project IDs
_cache: tuple[int, list[str]] = (0, [])

# cached version of the database 
_db_version = 0


def bump_db_version() -> int:
    global _db_version
    with _state_lock:
        _db_version += 1
        return _db_version

def get_db_version() -> int:
    """Needed to get the _db_version threadsafe outside of the database module"""
    with _state_lock:
        return _db_version
    
    

def get_all_project_ids() -> list[str]:
    """
    Retrieve a list of all project IDs from the merged DuckDB database.

    The list is sorted by the date of creation of the last file measured (descending).

    :return: List of all project IDs
    :rtype: list[str]
    """
    global _cache
    
    with _state_lock:
        version = _db_version
        if _cache and _cache[0] == version and version != 0:
            return _cache[1]

    try:
        with duckdb.connect(MergedDuckDB) as con:
            df = con.execute(
                """SELECT DISTINCT ProjectID FROM project_data
                ORDER BY DateTime DESC"""
            ).df()
        AllProjectNames: list[str] = df["ProjectID"].tolist()

        with _state_lock:
            if _db_version == version:
                _cache = (version, AllProjectNames)
        
        return AllProjectNames
    
    except Exception as e:
        logger.error(
            "project_id_fetch_failed",
            extra={"error_class": type(e).__name__, "error": str(e)}, exc_info=True)
        
        return []


def search_project_ids(pattern: str | None, limit: int = 100) -> list[str]:
    """Search project IDs using an optional text pattern.

    If a pattern is provided, returns IDs that contain the pattern case-insensitively.
    If no pattern is provided, returns the first `limit` project IDs from the cached list.

    :param pattern: Text pattern used to filter project IDs.
    :type pattern: str | None
    :param limit: Maximum number of project IDs to return.
    :type limit: int
    :return: Filtered list of project IDs.
    :rtype: list[str]
    """
    all_ids = get_all_project_ids()
    if not pattern:
        return all_ids[:limit]
    pattern_lower = pattern.lower()
    matches = [pid for pid in all_ids if pattern_lower in pid.lower()]
    return matches[:limit]
