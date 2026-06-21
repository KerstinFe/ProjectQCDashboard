from pathlib import Path
from dotenv import dotenv_values
from ProjectQCDashboard.config.RunningContainer import _is_running_in_container
from ProjectQCDashboard.config.schemas import EnvPaths
from datetime import datetime


# Base paths
PACKAGE_LOCATION = Path(__file__).resolve().parents[3]

if _is_running_in_container():
    internal_path =  Path("/data")
else:
    internal_path =  Path(PACKAGE_LOCATION) / "TestData_delete"


def setup_logging() -> str: 
    if _is_running_in_container():
        log_dir = "/logs"  # Use the mounted directory
    else:
        log_dir = Path(PACKAGE_LOCATION / "logs").as_posix()

    Path(log_dir).mkdir(parents=True, exist_ok=True)
    currentdate = datetime.now().strftime("%Y%m%d")

    return (Path(log_dir) / f"{currentdate}_message.log").as_posix()

log_filepath = setup_logging()

# Database configuration
class DatabasePaths:
    def __init__(self) -> None:
        """
        Centralized database path configuration for both container and local environments.
        Initialize all database paths based on the current runtime environment.

        This method sets up paths for merged DuckDB, MQQC databases, metadata database,
        and external sources, using environment variables and project structure.
        """
        self.merged_db: str  = ""
        self.meta_db: str  = ""
        self.mqqc_dbs: list[str] = []
        self.external_mqqc_dbs: list[str] = []
        self.external_meta_db: str = ""
        self.DB_Paths_towatch: list[str] = []
        
        self.paths_env = (
            dotenv_values(".env")
            if _is_running_in_container()
            else dotenv_values(".env.dev")
        )

        self._init_paths()

    def _read_env(self) -> EnvPaths:
        
        return EnvPaths(
            mqqc_db_name_e1=self.paths_env.get('MQQC_DB_NAME_E1') or 'list_collect.sqlite',
            mqqc_db_name_e2=self.paths_env.get('MQQC_DB_NAME_E2'),
            meta_db_e=self.paths_env.get('META_DB_NAME_E') or 'Metadata.sqlite',
            mqqc_db_name_1=self.paths_env.get('MQQC_DB_NAME_I1') or 'list_collect_1.sqlite',
            mqqc_db_name_2=self.paths_env.get('MQQC_DB_NAME_I2'),
            meta_db_name=self.paths_env.get('META_DB_NAME') or 'Metadata.sqlite',
            merged_db_name=self.paths_env.get('MERGED_DB_NAME') or 'mergedDB.db',
            mqqc_db_dir_1=self.paths_env.get('MQQC_DB1_DIR_CONTAINER') or '/external_db_1',
            mqqc_db_dir_2=self.paths_env.get('MQQC_DB2_DIR_CONTAINER') or '/external_db_2',
            meta_db_dir=self.paths_env.get('META_DB_DIR_CONTAINER') or '/external_db_3',
        )
    
    def _init_paths(self) -> None:
        env = self._read_env()

        # Create paths
        self.merged_db = str((internal_path / env.merged_db_name).as_posix())
        self.meta_db = str((internal_path / env.meta_db_name).as_posix())
        self.mqqc_dbs = [str((internal_path / env.mqqc_db_name_1).as_posix())]

        # External databases (read-only sources)
        self.external_mqqc_dbs = [str((Path(env.mqqc_db_dir_1) / env.mqqc_db_name_e1).as_posix())]
        self.external_meta_db = str((Path(env.meta_db_dir) / env.meta_db_e).as_posix())
        self.DB_Paths_towatch = [env.mqqc_db_dir_1, env.meta_db_dir]

        if env.mqqc_db_name_2 and env.mqqc_db_name_e2:
            self.external_mqqc_dbs.append(str((Path(env.mqqc_db_dir_2) / env.mqqc_db_name_e2).as_posix()))
            self.mqqc_dbs.append(str((internal_path / env.mqqc_db_name_2).as_posix()))
            self.DB_Paths_towatch = [env.mqqc_db_dir_1, env.mqqc_db_dir_2, env.meta_db_dir]

        if not _is_running_in_container() and (not self.paths_env.get('MQQC_DB1_DIR_CONTAINER') or not self.paths_env.get('META_DB_DIR_CONTAINER')):
            # If paths for external databases are not given 
            # then remove the external paths and paths to watch that were created with defaults so that there is no observer. 
            # Does not check for MQQC_DB2_DIR_CONTAINER since that is anyways optional.
            self.external_mqqc_dbs = []
            self.external_meta_db = ""
            self.DB_Paths_towatch = []

            


# Create singleton instance
db_paths = DatabasePaths()

MergedDuckDB = db_paths.merged_db
Metadata_DB = db_paths.meta_db
MQQC_DB = db_paths.mqqc_dbs 
external_mqqc = db_paths.external_mqqc_dbs 
external_meta = db_paths.external_meta_db
DB_Paths_towatch = db_paths.DB_Paths_towatch
