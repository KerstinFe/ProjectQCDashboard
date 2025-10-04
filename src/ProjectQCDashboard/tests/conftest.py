import sqlite3
import pytest
from pathlib import Path
from datetime import datetime
import ProjectQCDashboard.config.paths as paths

# @pytest.fixture
# def temp_mqqc_db(tmp_path: Path) -> str:
#     dbfile = tmp_path / "mqqc.sqlite"
#     con = sqlite3.connect(str(dbfile))
#     cur = con.cursor()
#     cur.execute(
#         "CREATE TABLE SingleFileReport (Name TEXT, \"System.Time.s\" TEXT, \"Intensity.100.\" REAL, AllPeptides INTEGER, uniPepCount INTEGER, Protein INTEGER);")
#     cur.execute(
#         "INSERT INTO SingleFileReport (Name, \"System.Time.s\", \"Intensity.100.\", AllPeptides, uniPepCount, Protein) VALUES (?,?,?,?,?,?)",
#         ("Astral_20250716_XYZ_HS_01", "2025-07-04 00:00:00", 123.0, 50, 10, 5))
#     con.commit()
#     con.close()
#     return str(dbfile)


# @pytest.fixture
# def temp_meta_db(tmp_path: Path) -> str:
#     dbfile = tmp_path / "meta.sqlite"
#     con = sqlite3.connect(str(dbfile))
#     cur = con.cursor()
#     cur.execute(
#         "CREATE TABLE Metadata_Sample (ProjectID TEXT, CreationDate TEXT, SampleName_ID TEXT);")
#     now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     cur.execute(
#         "INSERT INTO Metadata_Sample (ProjectID, CreationDate, SampleName_ID) VALUES (?,?,?)",
#         ("Astral_20250716_XYZ", now, "Astral_20250716_XYZ_HS_01.raw"))
#     con.commit()
#     con.close()
#     return str(dbfile)


@pytest.fixture
def csv_folder(tmp_path: Path, monkeypatch):
    """Patch ProjectQCDashboard.config.paths.CSVFolder and csvFiles_Folder to a temporary folder"""
    # CSVFolder exists; csvFiles_Folder may be absent depending on code version
    monkeypatch.setattr(paths, "CSVFolder", tmp_path)
    if hasattr(paths, "csvFiles_Folder"):
        monkeypatch.setattr(paths, "csvFiles_Folder", tmp_path)
    return tmp_path