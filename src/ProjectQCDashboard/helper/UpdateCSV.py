import os
import pandas as pd
import numpy as np
import csv
import re
from ProjectQCDashboard.helper.database import query, Database_Call
from ProjectQCDashboard.helper.common import convert_timestamps, removeLastNumber_fromFileName,IsStandardSample
from ProjectQCDashboard.config.paths import CSVFolder
from ProjectQCDashboard.helper.common import CreateOutputFilePath
from ProjectQCDashboard.config.logger import get_configured_logger
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

logger = get_configured_logger(__name__)

class CSVUpdater:
    def __init__(self, mqqc_db_path: Union[str, Path], metadata_db_path: Union[str, Path]) -> None:
        """
        Initialize the CSVUpdater with database paths.
        :param mqqc_db_path: The path to the MQQC database
        :type mqqc_db_path: Union[str, Path]
        :param metadata_db_path: The path to the metadata database
        :type metadata_db_path: Union[str, Path]
        """
        self.mqqc_db_path = mqqc_db_path
        self.metadata_db_path = metadata_db_path
        self.SQLRequest = '''SELECT Name,"System.Time.s", "Intensity.100.", 
                            "missed.cleavages.percent",AllPeptides ,uniPepCount, Protein 
                            FROM SingleFileReport'''
        self.SQLRequest_Project = '''SELECT Name,"System.Time.s", "Intensity.100.", 
                        "missed.cleavages.percent",AllPeptides ,uniPepCount, Protein 
                        FROM SingleFileReport
                        WHERE Name LIKE ?'''
        self.SQLRequest_Project_meta = '''SELECT * 
        FROM Metadata_Sample
        WHERE ProjectID LIKE ? '''
        # SQL headers plus the reformatted date
        # Note: After merge we'll have MQQC columns + Metadata columns + 3 date columns
        # We'll build this dynamically after the merge instead of hardcoding
        self.base_mqqc_headers = ["Name","System.Time.s", "Intensity.100.", 
                            "missed.cleavages.percent","AllPeptides","uniPepCount","Protein"]

    def _reformatRow(self, idx: int, row: Any, DateIdx: int) -> Any:
        """Reformat a row of the DataFrame.

        :param idx: The index of the row
        :type idx: int
        :param row: The row data
        :type row: Any
        :param DateIdx: The index of the date column
        :type DateIdx: int
        :return: The reformatted row
        :rtype: Any
        """
       
        row = row.to_list()
        date_str, time_str, date_time_str = convert_timestamps(row[DateIdx])
        return row + [date_str, time_str, date_time_str]

    

    def update_csv(self) -> None:

        """Update the CSV files with new data.
        :return: None
        :rtype: None
        """


        db = Database_Call(self.metadata_db_path)
        ProjectIDs_SqlRegex = db.getProjectNamesDict_SqlRegex()
        for ID, regexID in ProjectIDs_SqlRegex.items():
            logger.info(f"Processing {ID} with regex: {regexID}")
            try:
                results_ID_mqqc = query(self.mqqc_db_path, self.SQLRequest_Project, params=(regexID,))
                results_ID_metadata = query(self.metadata_db_path, self.SQLRequest_Project_meta, params=(ID,))

                results_ID_metadata["SampleName_ID"] = results_ID_metadata["SampleName_ID"].str.replace(".raw", "")
   
                OutputFilePath = CreateOutputFilePath(ID)
                logger.info(f"OutputFilePath = {OutputFilePath}")
                ''' I do righter join here because I assume that the metadata Project ID is more correct than the matching in MQQC database'''
                results_ID_joined = results_ID_mqqc.merge(results_ID_metadata, left_on="Name", right_on = "SampleName_ID", suffixes=("_mqqc", "_metadata"),how = 'right'  ) 
                results_ID_joined["Name"] = results_ID_joined["SampleName_ID"]
                results_ID_joined = results_ID_joined.drop(columns=["SampleName_ID"])
                DateIdx = results_ID_joined.columns.get_loc("CreationDate")
               
                all_rows = [self._reformatRow(idx, row, DateIdx) for idx, row in results_ID_joined.iterrows()]
                
                # Build column headers dynamically from the actual merged data
                column_headers = list(results_ID_joined.columns) + ['Date', 'Time', 'DateTime']
                
                sample_id_column = "Name"
                SampleIDIdx = column_headers.index(sample_id_column)
                df_new = pd.DataFrame(all_rows, columns=column_headers)
           
                if not os.path.exists(OutputFilePath):
                    logger.info(f"File does not exists {len(all_rows)} new rows for {ID}")
                    # File does not exist, write all rows with header
                    if all_rows:
                        df_new.to_csv(OutputFilePath, mode='a', header=True, index=False)
                    else:
                        logger.info(f"No rows to write for {ID}, skipping file creation")
                else:
                    try:
                        # Read existing CSV as strings for stable comparison
                        df_existing = pd.read_csv(OutputFilePath, sep=",", dtype=str)

                        # Ensure we compare the exact same set of columns in the same order
                        # column_headers was built from the new joined results and includes Date/Time columns
                        target_cols = list(column_headers)

                        # If existing file does not contain the same columns, consider it a difference
                        existing_cols = list(df_existing.columns)
                        if set(target_cols) != set(existing_cols):
                            logger.info(f"Column sets differ for {OutputFilePath}. Overwriting file.")
                            logger.debug(f"Existing cols: {existing_cols}, Target cols: {target_cols}")
                            df_new.to_csv(OutputFilePath, mode='w', header=True, index=False)
                            continue

                        elif target_cols != existing_cols:
                            logger.info(f"Columns are the same but order differs for {OutputFilePath}. Overwriting file.")
                            logger.debug(f"Existing cols: {existing_cols}, Target cols: {target_cols}")
                            df_new.to_csv(OutputFilePath, mode='w', header=True, index=False)
                            continue

                        elif target_cols == existing_cols:

                            # Index both dataframes by the sample id for easy comparison
                            # df_existing_idx = df_existing.set_index(sample_id_column)
                            # df_new_idx = df_new.set_index(sample_id_column)

                            existing_ids = set(df_existing[sample_id_column].astype(str))
                            new_ids = set(df_new[sample_id_column].astype(str))

                            common_ids = sorted(list(existing_ids & new_ids))
                            added_ids = sorted(list(new_ids - existing_ids))
                            # removed_ids = sorted(list(existing_ids - new_ids))

                            # Log diagnostics to help identify problematic projects
                            logger.debug(f"{ID}: existing_rows={len(df_existing)}, new_rows={len(df_new)}, common={len(common_ids)}, added={len(added_ids)}")

                            # If there are common ids, compare those rows exactly
                            if common_ids:
                                # Work with copies (don't rely on index alignment semantics)
                                df_existing_common = df_existing[df_existing[sample_id_column].isin(common_ids)].copy()
                                df_new_common = df_new[df_new[sample_id_column].isin(common_ids)].copy()

                                # # If there are duplicate sample IDs in either, treat as changed -> overwrite
                                # if df_existing_common[sample_id_column].duplicated().any() or df_new_common[sample_id_column].duplicated().any():
                                #     logger.info(f"Duplicate Sample IDs detected for {OutputFilePath}; overwriting file")
                                #     df_new.to_csv(OutputFilePath, mode='w', header=True, index=False)
                                #     continue

                                # Normalize helper: select target columns, stringify, strip whitespace, fill NA
                                # def _normalize_df(df_in: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
                                #     df2 = df_in.copy()
                                #     for c in cols:
                                #         if c not in df2.columns:
                                #             df2[c] = ''
                                #     df2 = df2[cols]
                                #     df2 = df2.astype(str).applymap(lambda x: x.strip())
                                #     df2 = df2.fillna('<NA>')
                                #     return df2

                                df_existing_norm = df_existing_common[target_cols]
                                df_new_norm = df_new_common[target_cols]

                                # Sort both by sample id to guarantee identical order, then reset index
                                df_existing_norm = df_existing_norm.sort_values(by=sample_id_column).reset_index(drop=True)
                                df_new_norm = df_new_norm.sort_values(by=sample_id_column).reset_index(drop=True)

                                # Compare equality of normalized common rows
                                try:
                                    common_equal = df_existing_norm.equals(df_new_norm)
                                except Exception:
                                    # Defensive fallback: if any comparison still fails, overwrite
                                    logger.exception(f"Error comparing common rows for {OutputFilePath}; overwriting file")
                                    df_new.to_csv(OutputFilePath, mode='w', header=True, index=False)
                                    continue

                            if common_equal:
                                # Existing rows match exactly; append only new rows if present
                                if added_ids:
                                    df_to_append = df_new[df_new[sample_id_column].isin(added_ids)].reset_index(drop=True)
                                    # Ensure append uses the same column ordering
                                    df_to_append = df_to_append[target_cols]
                                    df_to_append.to_csv(OutputFilePath, mode='a', header=False, index=False)
                                    logger.info(f"Appended {len(added_ids)} new rows to existing file {OutputFilePath}")
                                else:
                                    logger.info(f"No changes detected for {OutputFilePath}; leaving file unchanged")
                            else:
                                # Either overlapping rows changed or some existing rows were removed -> overwrite
                                logger.info(f"Detected changes in overlapping rows or removed rows for {OutputFilePath}; overwriting file")
                                df_new.to_csv(OutputFilePath, mode='w', header=True, index=False)
                        else:
                            # No common ids: treat this as either completely new set or totally different -> overwrite
                            logger.info(f"No overlapping sample IDs for {OutputFilePath}; overwriting file")
                            df_new.to_csv(OutputFilePath, mode='w', header=True, index=False)
                    except Exception:
                        logger.exception(f"Unhandled error while processing {ID}; skipping and continuing")
                        continue
            except Exception:
                logger.exception(f"Unhandled error in project loop for {ID}; continuing to next project")
                continue
                
            
    def FirstCreationOfCsvs(self) -> None:
        """Create the CSV files if they do not exist.
            :return: None
            :rtype: None
        """

        if not os.path.isdir(CSVFolder):
            logger.info("No Folder for csv Files yet, Folder is created")
            os.mkdir(CSVFolder)

        logger.info("Initial updating/creation of csv files")
        self.update_csv()


def update_df(OutputFilePath: Union[str, Path]) -> pd.DataFrame:
    """Update the DataFrame from the CSV file.
    :param OutputFilePath: Path to the output CSV file
    :type OutputFilePath: Union[str, Path]
    :return: The updated DataFrame
    :rtype: pd.DataFrame
    """

    df = pd.read_csv(OutputFilePath, sep=",")
    
    result = []
    for index, row in df.iterrows():
        if not IsStandardSample(row["Name"]):
            result.append(removeLastNumber_fromFileName(row["Name"]))
        elif re.search("HSstd",row["Name"]) is None:
            result.append("OtherStandard")
        else: 
            result.append("HSstd")

    df["FileType"] = result   
    return df
