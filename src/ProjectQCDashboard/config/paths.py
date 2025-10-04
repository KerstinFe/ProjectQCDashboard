
from pathlib import Path
import os
from ProjectQCDashboard.config.loadParams import  load_params
from ProjectQCDashboard.helper.RunningContainer import _is_running_in_container

# Resolve relative paths
BASE_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = Path(__file__).resolve().parents[1]  # Points to QCTemplate/
CONFIG_DIR = PACKAGE_ROOT / "config"
PACKAGE_LOCATION = Path(__file__).resolve().parents[3]  # Points to ../src/QCTemplate/


CSVFolder = PACKAGE_LOCATION / "csvFiles"
TempFolder = PACKAGE_LOCATION /  "TEMP"

log_dir = Path(PACKAGE_LOCATION/ "logs" ).as_posix()
os.makedirs(log_dir, exist_ok=True) 
log_filepath = Path(PACKAGE_LOCATION/ "logs" / "message.log").as_posix()

# Get runtime parameters
PARAMS = load_params()

Metadata_DB = PARAMS.get('data', {}).get('metadata_db_path')
DEFAULT_METADATA_DB = Metadata_DB
MQQC_DB = PARAMS.get('data', {}).get('mqqc_db_path')
DEFAULT_MQQC_DB = MQQC_DB

external_mqqc = None
external_meta = None


if _is_running_in_container():
    # Map default paths to external mounted paths in container

    Metadata_DB = PARAMS.get('data', {}).get('metadata_db_path')
    DEFAULT_METADATA_DB = Metadata_DB
    MQQC_DB = PARAMS.get('data', {}).get('mqqc_db_path')
    DEFAULT_MQQC_DB = MQQC_DB


    if "list_collect.sqlite" in MQQC_DB:
        external_mqqc = "/external_MQQC_database"
    else:
        external_mqqc = MQQC_DB

    if "Metadata.sqlite" in Metadata_DB:
        external_meta = "/external_Meta_database"
    else:
        external_meta = Metadata_DB

else:
    # Derived configuration (combines internal config with external params)
    if Metadata_DB == "Metadata.sqlite":
       DEFAULT_METADATA_DB = Path(PACKAGE_LOCATION /"Metadata.pruned.sqlite").as_posix()
    elif Metadata_DB and os.path.isfile(Metadata_DB):
       DEFAULT_METADATA_DB = Metadata_DB
    else:
        DEFAULT_METADATA_DB = Path(PACKAGE_LOCATION /Metadata_DB).as_posix() if Metadata_DB else Path(PACKAGE_LOCATION / "Metadata.pruned.sqlite").as_posix()

    if MQQC_DB == "list_collect.sqlite":
        DEFAULT_MQQC_DB = Path(PACKAGE_LOCATION /"list_collect.pruned.sqlite").as_posix()
    elif MQQC_DB and os.path.isfile(MQQC_DB):
        DEFAULT_MQQC_DB = MQQC_DB
    else:
        DEFAULT_MQQC_DB = Path(PACKAGE_LOCATION / MQQC_DB).as_posix() if MQQC_DB else Path(PACKAGE_LOCATION / "list_collect.pruned.sqlite").as_posix()


