"""Tests for SyncDatabases module."""

import sqlite3
from pathlib import Path
from ProjectQCDashboard.db.SyncDatabases import sync_database
from contextlib import closing

class TestSyncDatabase:
    """Tests for sync_database() — copies SQLite databases from source to destination."""

    def test_sync_preserves_content(self, temp_dir: Path, test_db_paths: dict[str, Path]) -> None:
        """Synced database contains the same rows as the source."""
        dest = temp_dir / "synced.sqlite"
        result = sync_database(str(test_db_paths["mqqc"]), str(dest))
        
        assert result is True

        with closing(sqlite3.connect(str(test_db_paths["mqqc"]))) as src:
            src_names = {r[0] for r in src.execute("SELECT Name FROM SingleFileReport").fetchall()}
        with closing(sqlite3.connect(str(dest))) as dst:
            dst_names = {r[0] for r in dst.execute("SELECT Name FROM SingleFileReport").fetchall()}

        assert src_names == dst_names

    def test_sync_list_of_databases(self, temp_dir: Path, test_db_paths: dict[str, Path]) -> None:
        """Syncing a list of source/destination pairs all succeed."""
        dest_mqqc = temp_dir / "mqqc_copy.sqlite"
        dest_meta = temp_dir / "meta_copy.sqlite"

        result = sync_database(
            [str(test_db_paths["mqqc"]), str(test_db_paths["meta"])],
            [str(dest_mqqc), str(dest_meta)],
        )

        assert result is True
        assert dest_mqqc.exists()
        assert dest_meta.exists()

    def test_sync_missing_source_returns_false(self, temp_dir: Path) -> None:
        """Returns False and does not crash when source database does not exist."""
        result = sync_database(
            str(temp_dir / "nonexistent.sqlite"),
            str(temp_dir / "dest.sqlite"),
        )

        assert result is False

    def test_sync_mismatched_list_lengths_returns_false(self, temp_dir: Path, test_db_paths: dict[str, Path]) -> None:
        """Returns False when source and destination lists have different lengths."""
        result = sync_database(
            [str(test_db_paths["mqqc"]), str(test_db_paths["meta"])],
            [str(temp_dir / "only_one_dest.sqlite")],
        )

        assert result is False

    def test_sync_overwrites_existing_destination(self, temp_dir: Path, test_db_paths: dict[str, Path]) -> None:
        """Syncing to an existing destination file overwrites it correctly."""
        dest = temp_dir / "synced.sqlite"

        # First sync
        sync_database(str(test_db_paths["mqqc"]), str(dest))
        # Second sync — should not error
        result = sync_database(str(test_db_paths["mqqc"]), str(dest))

        assert result is True
        with closing(sqlite3.connect(str(dest))) as con:
            count = con.execute("SELECT COUNT(*) FROM SingleFileReport").fetchone()[0]
        assert count == 261