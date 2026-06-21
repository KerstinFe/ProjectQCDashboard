"""Tests for ValidateDatabases module and database query helpers."""

import pytest
import duckdb
from pathlib import Path
from unittest.mock import patch
from ProjectQCDashboard.db.ValidateDatabases import (
    get_table_names,
    _validate_database,
    validate_databases,
)

from ProjectQCDashboard.db.database import bump_db_version, get_all_project_ids

class TestGetTableNames:
    """Tests for get_table_names() — returns list of tables in a SQLite database."""

    def test_returns_correct_tables_mqqc(self, test_db_paths: dict[str, Path]) -> None:
        """Returns the expected table name from the MQQC database."""
        tables = get_table_names(str(test_db_paths["mqqc"]))
        assert "SingleFileReport" in tables

    def test_returns_correct_tables_metadata(self, test_db_paths: dict[str, Path]) -> None:
        """Returns both expected tables from the metadata database."""
        tables = get_table_names(str(test_db_paths["meta"]))
        assert "Metadata_Sample" in tables
        assert "Metadata_Project" in tables

    def test_returns_empty_list_for_missing_db(self, temp_dir: Path) -> None:
        """Returns an empty list when the database file does not exist."""
        tables = get_table_names(str(temp_dir / "nonexistent.sqlite"))
        assert tables == []


class TestValidateDatabase:
    """Tests for _validate_database() — raises on missing file or missing tables."""

    def test_valid_database_passes(self, test_db_paths: dict[str, Path]) -> None:
        """No exception raised for a valid database with the required table."""
        # Should not raise
        _validate_database(str(test_db_paths["mqqc"]), ["SingleFileReport"], "MQQC")

    def test_missing_file_raises_file_not_found(self, temp_dir: Path) -> None:
        """Raises FileNotFoundError when the database file does not exist."""
        with pytest.raises(FileNotFoundError):
            _validate_database(str(temp_dir / "missing.sqlite"), ["SomeTable"])

    def test_missing_table_raises_value_error(self, test_db_paths: dict[str, Path]) -> None:
        """Raises ValueError when a required table is absent from the database."""
        with pytest.raises(ValueError, match="missing required tables"):
            _validate_database(str(test_db_paths["mqqc"]), ["NonExistentTable"])


class TestValidateDatabases:
    """Tests for validate_databases() — validates a set of databases at startup."""

    def test_valid_databases_pass(self, test_db_paths: dict[str, Path]) -> None:
        """No exception raised when all provided databases are valid."""
        validate_databases(
            external_mqqc_dbs=[str(test_db_paths["mqqc"])],
            external_meta_db=str(test_db_paths["meta"]),
        )

    def test_missing_mqqc_raises(self, temp_dir: Path, test_db_paths: dict[str, Path]) -> None:
        """Raises FileNotFoundError when the MQQC database is missing."""
        with pytest.raises(FileNotFoundError):
            validate_databases(
                external_mqqc_dbs=[str(temp_dir / "missing.sqlite")],
                external_meta_db=str(test_db_paths["meta"]),
            )

    def test_missing_meta_raises(self, temp_dir: Path, test_db_paths: dict[str, Path]) -> None:
        """Raises FileNotFoundError when the metadata database is missing."""
        with pytest.raises(FileNotFoundError):
            validate_databases(
                external_mqqc_dbs=[str(test_db_paths["mqqc"])],
                external_meta_db=str(temp_dir / "missing.sqlite"),
            )

    def test_no_arguments_does_not_raise(self) -> None:
        """Calling with no arguments (local mode with no external DBs) does not raise."""
        validate_databases()


class TestGetAllProjectIds:
    """Tests for get_all_project_ids() — queries project IDs from the merged DuckDB."""

    def test_returns_list_of_project_ids(self, temp_dir: Path) -> None:
        """Returns a non-empty list of project ID strings from a valid DuckDB."""
        db_path = temp_dir / "test_merged.db"
        import pandas as pd

        sample = pd.DataFrame({
            "ProjectID": ["ProjectA", "ProjectA", "ProjectB"],
            "DateTime": pd.date_range("2025-01-01", periods=3),
        })
        with duckdb.connect(str(db_path)) as con:
            con.execute("CREATE TABLE project_data AS SELECT * FROM sample")

        bump_db_version()    

        with patch("ProjectQCDashboard.db.database.MergedDuckDB", str(db_path)):
            result = get_all_project_ids()

        assert isinstance(result, list)
        assert "ProjectA" in result
        assert "ProjectB" in result

    def test_returns_empty_list_on_error(self, temp_dir: Path) -> None:
        """Returns an empty list when the database is missing or query fails."""
        with patch("ProjectQCDashboard.db.database.MergedDuckDB",
                   str(temp_dir / "nonexistent.db")):
            
            bump_db_version() 
            result = get_all_project_ids()

        assert result == []

    def test_results_are_ordered_by_datetime_desc(self, temp_dir: Path) -> None:
        """Projects are returned ordered by most recent DateTime first."""
        db_path = temp_dir / "test_merged.db"
        import pandas as pd

        sample = pd.DataFrame({
            "ProjectID": ["OldProject", "NewProject"],
            "DateTime": ["2024-01-01", "2025-06-01"],
        })
        with duckdb.connect(str(db_path)) as con:
            con.execute("CREATE TABLE project_data AS SELECT * FROM sample")

        bump_db_version()    

        with patch("ProjectQCDashboard.db.database.MergedDuckDB", str(db_path)):
            result = get_all_project_ids()

        assert result[0] == "NewProject"
        assert result[1] == "OldProject"