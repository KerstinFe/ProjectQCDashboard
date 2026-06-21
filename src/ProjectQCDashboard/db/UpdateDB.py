import duckdb
import os
import json
import datetime as dt
from ProjectQCDashboard.config.configuration import PLOT_CONFIG, UpdateLastXEntries, DB_CONFIG
from ProjectQCDashboard.config.paths import MergedDuckDB
from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.db.database import bump_db_version
from pathlib import Path

logger = get_configured_logger(__name__)


class DuckDBUpdater:
    def __init__(self, mqqc_db_path: list[str], metadata_db_path: str) -> None:
        """
        Handles updating and merging multiple MQQC and metadata databases into a single DuckDB database.

        Provides methods for full and incremental updates, merging logic, and schema alignment.
        
        :param mqqc_db_path: The path(s) to the MQQC database(s) - can be a single path or list of paths
        :type mqqc_db_path: list[str]
        :param metadata_db_path: The path to the metadata database
        :type metadata_db_path: str 
        """
        # Support both single path and list of paths
        if isinstance(mqqc_db_path, (str, Path)):
            self.mqqc_db_paths: list[str] = [str(mqqc_db_path)]
        else:
            self.mqqc_db_paths = [str(p) for p in mqqc_db_path]
        
        self.metadata_db_path = metadata_db_path

        logger.info(
            "duckdb_updater_initialized",
            extra={"mqqc_database_count": len(self.mqqc_db_paths)},
        )
        
        self.SQL_mergedDB_template = """
                WITH mqqc_all AS ({mqqc_union}),
                mqqc_regular AS (
                    SELECT * FROM (
                        SELECT *, ROW_NUMBER() OVER (PARTITION BY Name) AS rn
                        FROM mqqc_all
                        WHERE NOT REGEXP_MATCHES(Name, '(\\.raw|\\.d)$')
                    ) WHERE rn = 1
                ),
                mqqc_iqc_cte AS (
                    SELECT * FROM (
                        SELECT *, ROW_NUMBER() OVER (PARTITION BY REGEXP_REPLACE(Name, '(\\.raw|\\.d)$', '')) AS rn
                        FROM mqqc_all
                        WHERE REGEXP_MATCHES(Name, '(\\.raw|\\.d)$')                      
                    ) WHERE rn = 1
                ),
                meta_sample AS (SELECT * FROM meta_all.Metadata_Sample),
                 base AS(
                SELECT
                    {mqqc_select},
                    {mqqc_iqc_select},
                    meta_sample.* EXCLUDE (ProjectID),
                    COALESCE(REGEXP_REPLACE(meta_sample.SampleName_ID, '(\\.raw|\\.d)$', ''), mqqc_regular.Name, REGEXP_REPLACE(mqqc_iqc_cte.Name, '(\\.raw|\\.d)$', '')) AS RawFileName,
                   COALESCE(meta_sample.ProjectID, CONCAT_WS('_', list_extract(string_split(COALESCE(mqqc_regular.Name, REGEXP_REPLACE(mqqc_iqc_cte.Name, '(\\.raw|\\.d)$', '')), '_'), 1), list_extract(string_split(COALESCE(mqqc_regular.Name, REGEXP_REPLACE(mqqc_iqc_cte.Name, '(\\.raw|\\.d)$', '')), '_'), 2), list_extract(string_split(COALESCE(mqqc_regular.Name, REGEXP_REPLACE(mqqc_iqc_cte.Name, '(\\.raw|\\.d)$', '')), '_'), 3))) AS ProjectID,
                   CAST(COALESCE(CAST(meta_sample.CreationDate as timestamp),
                                MAKE_TIMESTAMP_MS(MULTIPLY(CAST(COALESCE(mqqc_regular."System.Time.s", mqqc_iqc_cte."System.Time.s") as BIGINT),1000))) as date) as Date,
                    CAST(COALESCE(CAST(meta_sample.CreationDate as timestamp),
                                    MAKE_TIMESTAMP_MS(MULTIPLY(CAST(COALESCE(mqqc_regular."System.Time.s", mqqc_iqc_cte."System.Time.s") as BIGINT),1000))) as time) as Time,
                    CAST(COALESCE(CAST(meta_sample.CreationDate as timestamp),
                                    MAKE_TIMESTAMP_MS(MULTIPLY(CAST(COALESCE(mqqc_regular."System.Time.s", mqqc_iqc_cte."System.Time.s") as BIGINT),1000))) as timestamp) as DateTime,
                    
                   CASE
                    WHEN COALESCE(REGEXP_REPLACE(meta_sample.SampleName_ID, '(\\.raw|\\.d)$', ''), mqqc_regular.Name, REGEXP_REPLACE(mqqc_iqc_cte.Name, '(\\.raw|\\.d)$', '')) LIKE '%HSstd%' THEN 'HSstd'
                    WHEN COALESCE(REGEXP_REPLACE(meta_sample.SampleName_ID, '(\\.raw|\\.d)$', ''), mqqc_regular.Name, REGEXP_REPLACE(mqqc_iqc_cte.Name, '(\\.raw|\\.d)$', '')) LIKE '%[Ss]tandar[dt]%' THEN 'OtherStandard'
                    ELSE REGEXP_REPLACE(COALESCE(REGEXP_REPLACE(meta_sample.SampleName_ID, '(\\.raw|\\.d)$', ''), mqqc_regular.Name, REGEXP_REPLACE(mqqc_iqc_cte.Name, '(\\.raw|\\.d)$', '')), '_[^_]*$', '')
                    END AS FileType
                    
                FROM mqqc_regular
                FULL JOIN mqqc_iqc_cte ON REGEXP_REPLACE(mqqc_iqc_cte.Name, '(\\.raw|\\.d)$', '') = mqqc_regular.Name
                FULL JOIN meta_sample
                    ON COALESCE(mqqc_regular.Name, REGEXP_REPLACE(mqqc_iqc_cte.Name, '(\\.raw|\\.d)$', '')) = REGEXP_REPLACE(meta_sample.SampleName_ID, '(\\.raw|\\.d)$', '')
                ) 
                SELECT
                    base.*,
                    meta_project.* EXCLUDE  (TimeRange, ProjectID)
                FROM base
                LEFT JOIN meta_all.Metadata_Project as meta_project
                    ON base.ProjectID = meta_project.ProjectID
            """

    
    def _count_rows(self, con: duckdb.DuckDBPyConnection) -> int:
            
            result = con.execute("SELECT COUNT(*) FROM project_data").fetchone()
            if not result:
                return 0
            return int(result[0])       

    def _record_update(self, con: duckdb.DuckDBPyConnection, row_count: int) -> None:
        mtime_dict = {}
        for mqqc in self.mqqc_db_paths:
            try:
                mtime_dict[mqqc] = dt.datetime.fromtimestamp(os.path.getmtime(mqqc))\
                                              .strftime("%Y-%m-%d %H:%M:%S" )
            except OSError:
                mtime_dict[mqqc] = "unavailable"   

        try:         
            mtime_dict["meta"] = dt.datetime.fromtimestamp(os.path.getmtime(self.metadata_db_path))\
                                              .strftime("%Y-%m-%d %H:%M:%S" )
        except OSError:
            mtime_dict["meta"] = "unavailable"    

        mtime_json = json.dumps(mtime_dict)

        con.execute(
            "INSERT INTO meta_data VALUES (current_localtimestamp(), ?, ?)",
            [mtime_json, row_count]
        )

    def _get_all_mqqc_columns(self, con: duckdb.DuckDBPyConnection) -> tuple[list[set[str]], set[str]]:
        """
        Get the union of all columns across all MQQC databases.

        :param con: DuckDB connection with attached databases
        :return: Tuple of (list of column sets per DB, set of all columns)
        :rtype: tuple[list[set[str]], set[str]]
        """
        list_columns = list()
        all_columns = set()

        for idx in range(len(self.mqqc_db_paths)):
            logger.debug(
                "getting_mqqc_columns",
                extra={"index": idx})
            
            schema = con.execute(f"DESCRIBE mqqc{idx}.SingleFileReport").fetchall()
            temp = [row[0] for row in schema]
            list_columns.append(set(temp))
            all_columns.update(temp)

        return list_columns, all_columns
    
    def _build_mqqc_union(self, con: duckdb.DuckDBPyConnection, config_columns: list[str]) -> tuple[str, str, str]:
        """
        Build a UNION query that aligns columns across all MQQC databases.

        Ensures all required columns are present, filling with NULLs where missing.

        :param con: DuckDB connection with attached databases
        :param config_columns: List of columns to select
        :return: Tuple of (union_query, mqqc_select, mqqc_iqc_select)
        :rtype: tuple[str, str, str]
        """
        # Get all available columns across all databases
        list_mqqc_cols, all_mqqc_cols = self._get_all_mqqc_columns(con)
        
        logger.debug(
            "all_mqqc_columns_resolved",
            extra={"columns_count": len(all_mqqc_cols)},
        )
        
        # Filter to columns we need (from config)
        needed_columns = list(set(all_mqqc_cols).intersection(set(config_columns)))
        
        # Build individual SELECT statements for each database
        union_parts = []
        for idx in range(len(self.mqqc_db_paths)):
            db_columns = list_mqqc_cols[idx]
            
            # Build SELECT clause with NULLs for missing columns
            select_parts = []
            for col in needed_columns:
                if col in db_columns:
                    select_parts.append(f'"{col}"')
                else:
                    select_parts.append(f'NULL AS "{col}"')
            
            select_clause = ', '.join(select_parts)

            # Because the select_clause columns are filtered against a inclusion list (needed_columns), this safeguards against sqlinjection.
            union_parts.append(f"SELECT {select_clause} FROM mqqc{idx}.SingleFileReport")
        
        # Combine with UNION ALL
        union_query = '\n            UNION ALL\n            '.join(union_parts)
        
        # Build the mqqc_select clause for the outer query (regular entries)
        mqqc_select = ', '.join([f'mqqc_regular."{col}"' for col in needed_columns])
        
        # Build the mqqc_iqc_select clause for iQC entries (columns suffixed with _iQC)
        mqqc_iqc_select = ', '.join([f'mqqc_iqc_cte."{col}" AS "{col}_iQC"' for col in needed_columns])
        
        logger.info(
            "mqqc_union_built",
            extra={
                "database_count": len(self.mqqc_db_paths),
                "needed_columns_count": len(needed_columns),
            },
        )
        return union_query, mqqc_select, mqqc_iqc_select

    def _attach_sources(self, con: duckdb.DuckDBPyConnection) -> None:   
        """
        Attach source databases. Used before _build_merge_query.

        :param con: DuckDB connection
        """
        
        for idx, mqqc_path in enumerate(self.mqqc_db_paths):
            
            # The databases are operator-configures in .env file 
            # and validated in validate_databases, so no further check necessary here.               
            con.execute(f"ATTACH '{mqqc_path}' AS mqqc{idx} (TYPE SQLITE, READ_ONLY)")
        
        con.execute(f"ATTACH '{self.metadata_db_path}' AS meta_all (TYPE SQLITE, READ_ONLY)")
        logger.info("databases_attached")

    def _build_merge_query(self, con: duckdb.DuckDBPyConnection) -> str:
        """
        Build the formatted merge query.

        This is the single source of truth for how MQQC and metadata are merged.
        Used by both create_initial_database and _incremental_update.

        :param con: DuckDB connection
        :return: Formatted SQL merge query
        :rtype: str
        """
        
        config_columns = DB_CONFIG + [config[0] for config in PLOT_CONFIG.values()]
        mqqc_union, mqqc_select, mqqc_iqc_select = self._build_mqqc_union(con, config_columns)
        
        logger.debug(
            "merge_query_debug_info",
            extra={
                "config_columns": config_columns,
                "mqqc_select": mqqc_select,
                "mqqc_iqc_select": mqqc_iqc_select,
            },
        )
        return self.SQL_mergedDB_template.format(
            mqqc_union=mqqc_union,
            mqqc_select=mqqc_select,
            mqqc_iqc_select=mqqc_iqc_select
        )

    def update_db(self, num_recent_rows: int = UpdateLastXEntries, force_full_refresh: bool = False) -> None:
        """
        Update the DuckDB database with new data.

        By default, performs incremental update using the most recent rows from metadata.
        Set force_full_refresh=True for nightly complete rebuild.

        :param num_recent_rows: Number of most recent rows to fetch from metadata (default 50)
        :type num_recent_rows: int
        :param force_full_refresh: If True, performs complete rebuild instead of incremental
        :type force_full_refresh: bool
        """
        
        if force_full_refresh:
            logger.info("duckdb_full_refresh_started")
            self.create_initial_database()  

        else:
            logger.info(
                "duckdb_incremental_update_started",
                extra={"recent_rows": num_recent_rows},
            )
            self._incremental_update(num_recent_rows)

        bump_db_version()

    
    def _incremental_update(self, num_recent_rows: int = UpdateLastXEntries) -> None:
        """
        Perform incremental update using most recent rows from metadata.

        Deletes and reinserts only the most recent samples for efficiency.

        :param num_recent_rows: Number of most recent rows to process
        :type num_recent_rows: int
        """
        with duckdb.connect(MergedDuckDB) as con:
            con.execute("LOAD sqlite_scanner")
            self._attach_sources(con)
            sql_query = self._build_merge_query(con)

                      
            total_rows_initial = self._count_rows(con)
                    
            # Build query to get recent samples from all MQQC databases
            mqqc_recent_parts = []
            for idx in range(len(self.mqqc_db_paths)):
                mqqc_recent_parts.append(f""" SELECT sample_id, Time FROM (
                        SELECT REGEXP_REPLACE(Name, '(\\.raw|\\.d)$', '') AS sample_id, 
                                MAKE_TIMESTAMP_MS(MULTIPLY(CAST(SF_report."System.Time.s" as BIGINT),1000)) AS Time
                        FROM mqqc{idx}.SingleFileReport as SF_report
                        ORDER BY Time DESC
                        LIMIT {num_recent_rows}
                        )
                
                    """)
            
            mqqc_recent_union = '\n   UNION ALL \n   '.join(mqqc_recent_parts)
          
            
            recent_samples_df = con.execute(f""" SELECT * FROM (
                        SELECT DISTINCT REGEXP_REPLACE(SampleName_ID, '(\\.raw|\\.d)$', '') AS sample_id, CAST(meta_sample.CreationDate as timestamp) as Time
                        FROM meta_all.Metadata_Sample AS meta_sample
                        ORDER BY Time DESC
                        LIMIT {num_recent_rows}
                        )
                        UNION ALL

                        ({mqqc_recent_union})
                        """).fetchdf()
            
            recent_samples = recent_samples_df['sample_id'].tolist()
            logger.debug(
                    "recent_samples_identified",
                    extra={"recent_samples": recent_samples},
                )
            
            if not recent_samples:
                logger.info("no_recent_samples_to_update")
                return
                
            logger.info(
                    "processing_recent_samples",
                    extra={"sample_count": len(recent_samples)},
                )
            
            cols = [r[0] for r in con.execute("DESCRIBE project_data").fetchall()]
            set_clause   = ", ".join(f'"{c}" = upserts."{c}"' for c in cols if c != "RawFileName")
            insert_cols  = ", ".join(f'"{c}"' for c in cols)
            insert_vals  = ", ".join(f'upserts."{c}"' for c in cols)

            
            query =  f"""
                            MERGE INTO project_data as p
                            USING(
                                SELECT * EXCLUDE (rn) FROM (
                                    SELECT *, ROW_NUMBER() OVER (PARTITION BY RawFileName) AS rn
                                    FROM ({sql_query}) AS sub
                                    WHERE RawFileName IN (SELECT unnest(?))
                                ) WHERE rn = 1
                                ) AS upserts
                            ON (upserts.RawFileName = p.RawFileName)
                            WHEN MATCHED THEN UPDATE SET {set_clause}
                            WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({insert_vals});

                        """  
            
            try:
                con.execute(query, [recent_samples])
                total_rows = self._count_rows(con)
                self._record_update(con, total_rows) 

            except Exception as e:
                logger.error("incremental_update_failed",
                extra={ "error_class": type(e).__name__, "error": str(e)}, exc_info=True)
                raise 
            
            logger.info("incremental_update_complete", extra={
                    "samples_processed": len(recent_samples),
                    "rows_before": total_rows_initial,
                    "rows_final": total_rows,
                })
            
           
    def create_initial_database(self) -> None:
        """
        Create the DuckDB database if it does not exist.

        This method performs a full database initialization by:
        - Loading all data from MQQC and metadata databases
        - Performing a FULL JOIN across all databases
        - Creating indexes for efficient querying
        """
        try:
            logger.info(
                "database_creation_started",
                extra={"merged_db": MergedDuckDB},
            )
            
            with duckdb.connect(MergedDuckDB) as con:
                logger.info("sqlite_scanner_loading")
                con.execute("LOAD sqlite_scanner")
                
                self._attach_sources(con)
                sql_query = self._build_merge_query(con)
        
                logger.info("duckdb_create_table_started")
                con.execute(f"CREATE OR REPLACE TABLE project_data AS {sql_query} ")
                logger.info("duckdb_table_created")
                # WHERE 1=0 -> if I want it to be empty
                con.execute("CREATE INDEX IF NOT EXISTS idx_project ON project_data(ProjectID)")
                con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_rawfile ON project_data(RawFileName)")
                logger.info("duckdb_index_created")
                
                con.execute(f"""CREATE OR REPLACE TABLE meta_data (
                                updated_at TIMESTAMP,
                                source_mtimes JSON,
                                row_count INTEGER
                            )""")
                
                total_rows_initial = self._count_rows(con)
                self._record_update(con, total_rows_initial)   
     
            logger.info(
                "database_initialization_complete",
                extra={"merged_db": MergedDuckDB},
            )

        except Exception as e:
            logger.error(
                "database_initialization_failed",
                extra={"merged_db": MergedDuckDB, 
                       "error_class": type(e).__name__, "error": str(e)}, exc_info=True)
            raise
        
    
        
  