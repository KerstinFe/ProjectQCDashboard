from pydantic import BaseModel, Field

class EnvPaths(BaseModel):
    mqqc_db_name_e1: str
    mqqc_db_name_e2: str | None
    meta_db_e: str
    mqqc_db_name_1: str
    mqqc_db_name_2: str | None
    meta_db_name: str
    merged_db_name: str
    mqqc_db_dir_1: str
    mqqc_db_dir_2: str
    meta_db_dir: str

class ProcessingConfig(BaseModel):
    PollingIntervalSeconds: int = Field(gt=0)
    ThresholdForTwoColumnsOfGraphs: int = Field(gt=0)
    ThresholdForRollingMean: int = Field(gt=1)
    UpdateLastXEntries: int = Field(gt=1)

class DataConfig(BaseModel):
    Tables_Metadata_db: list[str]
    Tables_MQQC_db: list[str]

class ColumnConfig(BaseModel):
    PLOT_CONFIG: list[tuple[str, tuple[str, str, str]]]
    DB_CONFIG: list[str]   
    TABLE_CONFIG: list[str]  

class Params(BaseModel):
    LOG_LEVEL: str = "INFO"
    data: DataConfig
    processing: ProcessingConfig
    ColumnsDatabase: ColumnConfig