"""Tests for UpdateDB module — DuckDBUpdater creates and incrementally updates the merged DuckDB."""

import duckdb
from unittest.mock import patch
from ProjectQCDashboard.db.UpdateDB import DuckDBUpdater
from pathlib import Path
from typing import Any
import sqlite3, shutil
from contextlib import closing

class TestDuckDBUpdaterInit:
    """Tests for DuckDBUpdater initialisation."""

    def test_single_path_normalised_to_list(self, test_db_paths: dict[str, Path]) -> None:
        """A single string path is stored internally as a one-element list."""
        updater = DuckDBUpdater([str(test_db_paths["mqqc"])], str(test_db_paths["meta"]))
        assert isinstance(updater.mqqc_db_paths, list)
        assert len(updater.mqqc_db_paths) == 1

    def test_list_of_paths_preserved(self, test_db_paths: dict[str, Path]) -> None:
        """A list of paths is stored as-is."""
        updater = DuckDBUpdater(
            [str(test_db_paths["mqqc"]), str(test_db_paths["mqqc"])],
            str(test_db_paths["meta"]),
        )
        assert len(updater.mqqc_db_paths) == 2


class TestCreateInitialDatabase:
    """Tests for DuckDBUpdater.create_initial_database() — full merge from SQLite sources."""

    def test_creates_project_data_table(self, temp_dir: Path, test_db_paths: dict[str, Path]) -> None:
        """create_initial_database() produces a DuckDB file containing project_data."""
        db_path = temp_dir / "merged.db"
        updater = DuckDBUpdater([str(test_db_paths["mqqc"])], str(test_db_paths["meta"]))

        with patch("ProjectQCDashboard.db.UpdateDB.MergedDuckDB", str(db_path)):
            updater.create_initial_database()

        assert db_path.exists()
        with duckdb.connect(str(db_path)) as con:
            tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
        assert "project_data" in tables

    def test_merged_table_has_rows(self, temp_dir: Path, test_db_paths: dict[str, Path]) -> None:
        """The merged table is non-empty after a full initialisation."""
        db_path = temp_dir / "merged.db"
        updater = DuckDBUpdater([str(test_db_paths["mqqc"])], str(test_db_paths["meta"]))

        with patch("ProjectQCDashboard.db.UpdateDB.MergedDuckDB", str(db_path)):
            updater.create_initial_database()

        with duckdb.connect(str(db_path)) as con:
            result = con.execute("SELECT COUNT(*) FROM project_data").fetchone()
            if result is None:
                count = 0
            else:     
                count = result[0]
        assert count > 0

    def test_project_id_column_populated(self, temp_dir: Path, test_db_paths: dict[str, Path]) -> None:
        """The ProjectID column contains known project IDs from the metadata."""
        db_path = temp_dir / "merged.db"
        updater = DuckDBUpdater([str(test_db_paths["mqqc"])], str(test_db_paths["meta"]))

        with patch("ProjectQCDashboard.db.UpdateDB.MergedDuckDB", str(db_path)):
            updater.create_initial_database()

        with duckdb.connect(str(db_path)) as con:
            project_ids = {
                r[0] for r in con.execute(
                    "SELECT DISTINCT ProjectID FROM project_data WHERE ProjectID IS NOT NULL"
                ).fetchall()
            }
        assert len(project_ids) > 0
        # All IDs should be non-empty strings
        assert all(isinstance(pid, str) and len(pid) > 0 for pid in project_ids)

    def test_datetime_column_populated(self, temp_dir: Path, test_db_paths: dict[str, Path]) -> None:
        """The DateTime column is populated for rows that have a CreationDate in metadata."""
        db_path = temp_dir / "merged.db"
        updater = DuckDBUpdater([str(test_db_paths["mqqc"])], str(test_db_paths["meta"]))

        with patch("ProjectQCDashboard.db.UpdateDB.MergedDuckDB", str(db_path)):
            updater.create_initial_database()

        with duckdb.connect(str(db_path)) as con:
            result = con.execute(
                "SELECT COUNT(*) FROM project_data WHERE DateTime IS NOT NULL"
            ).fetchone()

            if result is None:
                count_with_datetime = 0
            else:     
                count_with_datetime = result[0]
        assert count_with_datetime > 0

    def test_index_created(self, temp_dir: Path, test_db_paths: dict[str, Path]) -> None:
        """An index on ProjectID exists after initialisation."""
        db_path = temp_dir / "merged.db"
        updater = DuckDBUpdater([str(test_db_paths["mqqc"])], str(test_db_paths["meta"]))

        with patch("ProjectQCDashboard.db.UpdateDB.MergedDuckDB", str(db_path)):
            updater.create_initial_database()

        with duckdb.connect(str(db_path)) as con:
            indexes = con.execute(
                "SELECT index_name FROM duckdb_indexes() WHERE table_name = 'project_data'"
            ).fetchall()
        index_names = [r[0] for r in indexes]
        assert "idx_project" in index_names

    def test_create_initial_is_idempotent(self, temp_dir: Path, test_db_paths: dict[str, Path]) -> None:
        """Calling create_initial_database() twice does not raise (IF NOT EXISTS guard)."""
        db_path = temp_dir / "merged.db"
        updater = DuckDBUpdater([str(test_db_paths["mqqc"])], str(test_db_paths["meta"]))

        with patch("ProjectQCDashboard.db.UpdateDB.MergedDuckDB", str(db_path)):
            updater.create_initial_database()
            updater.create_initial_database()  # Should not raise

    def test_multiple_mqqc_databases(self, temp_dir: Path, test_db_paths: dict[str, Path]) -> None:
        """Merging two identical MQQC databases doubles the row count (UNION ALL)."""
        db_path = temp_dir / "merged.db"
        updater = DuckDBUpdater(
            [str(test_db_paths["mqqc"]), str(test_db_paths["mqqc"])],
            str(test_db_paths["meta"]),
        )

        with patch("ProjectQCDashboard.db.UpdateDB.MergedDuckDB", str(db_path)):
            updater.create_initial_database()

        with duckdb.connect(str(db_path)) as con:
            result = con.execute("SELECT COUNT(*) FROM project_data").fetchone()
            if result is None:
                count = 0
            else:     
                count = result[0]

        # Single DB merged count for reference
        db_path_single = temp_dir / "merged_single.db"
        updater_single = DuckDBUpdater([str(test_db_paths["mqqc"])], str(test_db_paths["meta"]))
        with patch("ProjectQCDashboard.db.UpdateDB.MergedDuckDB", str(db_path_single)):
            updater_single.create_initial_database()
        with duckdb.connect(str(db_path_single)) as con:
            result = con.execute("SELECT COUNT(*) FROM project_data").fetchone()
            if result is None:
                count_single = 0
            else:     
                count_single = result[0]

        assert count == count_single


class TestIncrementalUpdate:
    """Tests for DuckDBUpdater.update_db() in incremental mode."""

    def _create_initial(self, db_path: str | Path, test_db_paths: dict[str, Path]) -> Any:
        """Helper: run create_initial_database with patched MergedDuckDB path."""
        updater = DuckDBUpdater([str(test_db_paths["mqqc"])], str(test_db_paths["meta"]))
        with patch("ProjectQCDashboard.db.UpdateDB.MergedDuckDB", str(db_path)):
            updater.create_initial_database()
        return updater

    def test_incremental_update_does_not_crash(self, temp_dir: Path, test_db_paths: dict[str, Path]) -> None:
        """update_db() in incremental mode completes without raising."""
        db_path = temp_dir / "merged.db"
        updater = self._create_initial(db_path, test_db_paths)

        with patch("ProjectQCDashboard.db.UpdateDB.MergedDuckDB", str(db_path)):
            updater.update_db()  # Should not raise

    def test_force_full_refresh_recreates_table(self, temp_dir: Path, test_db_paths: dict[str, Path]) -> None:
        """force_full_refresh=True drops and recreates project_data."""
        db_path = temp_dir / "merged.db"
        updater = self._create_initial(db_path, test_db_paths)

        with duckdb.connect(str(db_path)) as con:
            result = con.execute("SELECT COUNT(*) FROM project_data").fetchone()
            if result is None:
                count_before = 0
            else:     
                count_before = result[0]

        with patch("ProjectQCDashboard.db.UpdateDB.MergedDuckDB", str(db_path)):
            updater.update_db(force_full_refresh=True)

        with duckdb.connect(str(db_path)) as con:
            result = con.execute("SELECT COUNT(*) FROM project_data").fetchone()
            if result is None:
                count_after = 0
            else:     
                count_after = result[0]

        # Row count should be the same after a full refresh with the same source data
        assert count_after == count_before
        

    def test_incremental_upsert_changes_only_the_edited_row(
        self, temp_dir: Path, test_db_paths: dict[str, Path]
    ) -> None:
        """Editing one source sample updates exactly that merged row (by name),
        to the new value, and leaves every other row identical."""
        # writable copies of the read-only fixtures
        mqqc = temp_dir / "mqqc.sqlite"
        shutil.copy(test_db_paths["mqqc"], mqqc)

        db_path = temp_dir / "merged.db"
        updater = DuckDBUpdater([str(mqqc)], str(test_db_paths["meta"]))
        with patch("ProjectQCDashboard.db.UpdateDB.MergedDuckDB", str(db_path)):
            updater.create_initial_database()

        def snapshot() -> dict[Any, dict[str, Any]]:
            with duckdb.connect(str(db_path)) as con:
                cols = [c[0] for c in con.execute("DESCRIBE project_data").fetchall()]
                rows = con.execute("SELECT * FROM project_data").fetchall()
            return {dict(zip(cols, r))["RawFileName"]: dict(zip(cols, r)) for r in rows}

        before = snapshot()

        ## values to update the database 
        # I update the Protein column in one row to 9999
         
        METRIC_COL = "Protein" 
        new_value  = "99999" 

        with closing(sqlite3.connect(mqqc)) as con:
            with con:
                src_key = con.execute(f"SELECT Name FROM SingleFileReport LIMIT 1").fetchone()[0]
                con.execute(f"UPDATE SingleFileReport SET {METRIC_COL} = ? WHERE Name = ?",
                        (new_value, src_key))

        with patch("ProjectQCDashboard.db.UpdateDB.MergedDuckDB", str(db_path)):
            updater.update_db()  # incremental upsert

        after = snapshot()
        
        assert set(after) == set(before)                    # no rows added or dropped
        changed = [k for k in before if after[k] != before[k]]
        assert len(changed) == 1                            # exactly one row moved
        row = changed[0]
        assert after[row][METRIC_COL] == new_value          # ...to the value we set
        assert {c: v for c, v in after[row].items() if c != METRIC_COL} == \
            {c: v for c, v in before[row].items() if c != METRIC_COL}  # rest of that row intact


def test_iqc_alignment_and_dedup(iqc_sources: tuple[str, str, str]) -> None:
    mqqc, meta, merged = iqc_sources

    updater = DuckDBUpdater([mqqc], meta)
    updater.create_initial_database()

    with duckdb.connect(merged) as con:
        rows = con.execute(
            'SELECT RawFileName, "Metric", "Metric_iQC" '
            'FROM project_data ORDER BY RawFileName'
        ).fetchall()

    # Regular+iQC twin collapse to one row; duplicate regular deduped; iQC-only survives; regular only survives -> 3 rows
    assert len(rows) == 3
    assert [r[0] for r in rows] == ["Proj_A_01_S1", "Proj_A_01_S2", "Proj_A_01_S3"]

    s1, s2, s3 = rows  # SELECT RawFileName, "Metric", "Metric_iQC" ... ORDER BY RawFileName
    assert s1[1] == 1000.0   # regular
    assert s1[2] == 2000.0   # iQC on the same row
    assert s2[1] is None     # iQC-only
    assert s2[2] == 2500.0
    assert s3[1] == 3000.0
    assert s3[2] is None