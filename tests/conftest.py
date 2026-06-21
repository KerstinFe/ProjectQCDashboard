"""Pytest configuration and fixtures for ProjectQCDashboard tests."""

import pytest
import tempfile
import shutil
from pathlib import Path
import sqlite3
from typing import Generator,Any
import ProjectQCDashboard.db.UpdateDB as UpdateDB
from _pytest.monkeypatch import MonkeyPatch
from ProjectQCDashboard.config.paths import internal_path

@pytest.fixture
def temp_dir() -> Generator[Any, Any, Any]:
    """Create a temporary directory that is automatically cleaned up after the test."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)
 
 
@pytest.fixture
def test_db_paths() -> dict[str | Path, str | Path]:
    """Paths to the pruned SQLite test databases included in the repository."""
    base = Path(__file__).parent.parent
    return {
        "mqqc": base / "TestData"/ "list_collect.pruned.sqlite",
        "meta": base / "TestData"/ "Metadata.pruned.sqlite",
    }
 
@pytest.fixture
def iqc_sources(tmp_path: Path, monkeypatch: MonkeyPatch) -> tuple[str, str, str]:
    """Tiny SQLite MQQC + metadata sources that exercise iQC alignment."""
    mqqc = tmp_path / "mqqc.sqlite"
    meta = tmp_path / "meta.sqlite"
    merged = tmp_path / "merged.duckdb"

    ### create mini sqlite mqqc with test rows
    con = sqlite3.connect(mqqc)
    con.execute('CREATE TABLE SingleFileReport ("Name" TEXT, "System.Time.s" REAL, "Metric" REAL)')
    con.executemany('INSERT INTO SingleFileReport VALUES (?, ?, ?)', [
        ("Proj_A_01_S1",     1755439995, 1000),  # regular
        ("Proj_A_01_S1.raw", 1755439995, 2000),  # iQC twin
        ("Proj_A_01_S1",     1755439995, 1000),  # duplicated row -> test that only one is kept
        ("Proj_A_01_S2.raw", 1755442365, 2500),  # iQC with no regular twin
        ("Proj_A_01_S3",     1755439900, 3000),  # entry with no iQC twin
    ])
    con.commit(); con.close()

    ### create empty meta data table because we need it for merge
    con = sqlite3.connect(meta)
    con.execute('CREATE TABLE Metadata_Sample ("SampleName_ID" TEXT, "ProjectID" TEXT, "CreationDate" TEXT)')
    con.execute('CREATE TABLE Metadata_Project ("ProjectID" TEXT, "TimeRange" TEXT, "ProjectName" TEXT)')
    con.commit(); con.close()

    # Redirect the merge output and pin the column config so the fixture schema stays minimal.
    monkeypatch.setattr(UpdateDB, "MergedDuckDB", str(merged))
    monkeypatch.setattr(UpdateDB, "DB_CONFIG", ["Name", "System.Time.s", "Metric"])
    monkeypatch.setattr(UpdateDB, "PLOT_CONFIG", {})

    return str(mqqc), str(meta), str(merged)

@pytest.fixture(scope="session", autouse=True)
def _cleanup_internal_path() -> Generator[None, None, None]:
    yield
    shutil.rmtree(internal_path, ignore_errors=True)