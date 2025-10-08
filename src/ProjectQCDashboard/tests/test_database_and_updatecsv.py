import os
import pandas as pd
from pathlib import Path
import sqlite3
from ProjectQCDashboard.helper.database import Database_Call, query
from ProjectQCDashboard.components.UserInput import GetTableNames
from ProjectQCDashboard.helper.UpdateCSV import CSVUpdater



def create_temp_metadata_db(tmp_path):
    db_path = tmp_path / "Metadata.sqlite"
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    # Create minimal Metadata_Sample table
    cur.execute(
        """
        CREATE TABLE Metadata_Sample (
            SampleName_ID TEXT,
            ProjectID TEXT,
            CreationDate TEXT
        )
        """
    )
    # Insert one sample row
    cur.execute(
        "INSERT INTO Metadata_Sample (SampleName_ID, ProjectID, CreationDate) VALUES (?,?,?)",
        ("QExactive_20250728_XYZ_HS_01.raw", "QExactive_20250728_XYZ", "2025-08-01 12:00:00"),
    )

    cur.execute(
        """
       CREATE TABLE Metadata_Project (
                    ProjectID	TEXT,
                    ProjectID_Date	TEXT
        )
        """
    )
    # Insert one project row
    cur.execute(
        "INSERT INTO Metadata_Project (ProjectID, ProjectID_Date) VALUES (?,?)",
        ("QExactive_20250728_XYZ", "20250728"),
    )
    con.commit()
    con.close()
    return db_path.as_posix()



def create_temp_mqqc_db(tmp_path):
    db_path = tmp_path / "list_collect.sqlite"
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    # Create minimal SingleFileReport table
    cur.execute(
        """
        CREATE TABLE SingleFileReport (
            Name TEXT,
            "System.Time.s" TEXT,
            "Intensity.100." REAL,
            "missed.cleavages.percent" REAL,
            AllPeptides INTEGER,
            uniPepCount INTEGER,
            Protein INTEGER
        )
        """
    )
    # Insert a row matching the metadata sample name
    cur.execute(
        "INSERT INTO SingleFileReport (Name, \"System.Time.s\", \"Intensity.100.\", \"missed.cleavages.percent\", AllPeptides, uniPepCount, Protein) VALUES (?,?,?,?,?,?,?)",
        ("sample1", "2025-08-01 12:00:00", 100.0, 0.5, 50, 45, 10),
    )
    con.commit()
    con.close()
    return db_path.as_posix()



def test_database_call_and_query(tmp_path):
    # Use pruned databases instead of creating temporary ones
    metadata_db = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../Metadata.pruned.sqlite'))
    mqqc_db = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../list_collect.pruned.sqlite'))

    if not os.path.exists(metadata_db):
        # use the temp db creation functions if the pruned dbs do not exist
        metadata_db = create_temp_metadata_db(tmp_path)
        mqqc_db = create_temp_mqqc_db(tmp_path)

    # Basic GetTableNames
    names_meta = GetTableNames(metadata_db)
    assert "Metadata_Sample" in names_meta
    assert "Metadata_Project" in names_meta

    names_mqqc = GetTableNames(mqqc_db)
    assert "SingleFileReport" in names_mqqc
   
    # query should return a DataFrame
    df = query(metadata_db, "SELECT * FROM Metadata_Sample")
    assert isinstance(df, pd.DataFrame)
    # If we created the DB in tmp_path (test mode) expect 1 row, otherwise expect the pruned DB size
    if str(tmp_path) in str(metadata_db):
        assert df.shape[0] == 1
    else:
        assert df.shape[0] == 263

    # query should return a DataFrame
    df = query(mqqc_db, "SELECT * FROM SingleFileReport")
    assert isinstance(df, pd.DataFrame)
    # If we created the DB in tmp_path (test mode) expect 1 row, otherwise expect the pruned DB size
    if str(tmp_path) in str(mqqc_db):
        assert df.shape[0] == 1
    else:
        assert df.shape[0] == 263

    # Database_Call with metadata DB should return dict of projects (uses timestamp filter)
    db_call = Database_Call(metadata_db)
    projects = db_call.getProjectNamesDict("regex")
    # function filters by sample name pattern; ensure returned type
    assert isinstance(projects, dict)



def test_csv_updater_first_creation(tmp_path,csv_folder, monkeypatch):
    # Use pruned databases instead of creating temporary ones
    metadata_db = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../Metadata.pruned.sqlite'))
    mqqc_db = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../list_collect.pruned.sqlite'))

    if not os.path.exists(metadata_db):
        # use the temp db creation functions if the pruned dbs do not exist
        metadata_db = create_temp_metadata_db(tmp_path)
        mqqc_db = create_temp_mqqc_db(tmp_path)

    # Monkeypatch CSVFolder referenced in modules that imported it at import time
    monkeypatch.setattr(
        "ProjectQCDashboard.config.paths.PACKAGE_LOCATION",
        Path(tmp_path),
    )
    monkeypatch.setenv("PYTHONPATH", os.getcwd())

    # Ensure all modules that imported CSVFolder earlier point to our tmp csv folder
    monkeypatch.setattr("ProjectQCDashboard.config.paths.CSVFolder", csv_folder)
    monkeypatch.setattr("ProjectQCDashboard.helper.common.CSVFolder", csv_folder)
    monkeypatch.setattr("ProjectQCDashboard.helper.UpdateCSV.CSVFolder", csv_folder)

    updater = CSVUpdater(mqqc_db, metadata_db)
    # Should create csv files without raising
    updater.FirstCreationOfCsvs()

    # Check that a file for the project exists
    expected_file = csv_folder / "QExactive_20250728_XYZ_ProjectData.csv"
    assert expected_file.exists()
    df = pd.read_csv(expected_file)
    assert not df.empty
