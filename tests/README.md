# Tests for ProjectQCDashboard

Test suite for ProjectQCDashboard. It deliberately mixes two styles: integration-style
tests that run against small, anonymized SQLite/DuckDB fixtures committed to the repo,
and unit tests that mock the database layer to exercise the data-processing and figure
logic in isolation.

## Requirements

Test dependencies (`pytest`, `pytest-cov`, `pytest-mock`) are declared in the 
`dev` dependency group in `pyproject.toml` and installed by `uv sync`.

## Running Tests

```bash
pytest                                               # all tests
pytest -v                                            # verbose
pytest tests/test_updatedDB.py                       # a single file
pytest --cov-report markdown:cov.md    # with coverage report
```

## Test Organization

- `conftest.py` — shared fixtures (`temp_dir`, `test_db_paths`)
- `test_sync_databases.py` — `sync_database()`: atomic SQLite source → destination copy
- `test_updatedDB.py` — `DuckDBUpdater`: full merge (`create_initial_database`) and incremental upsert (`update_db`)
- `test_database.py` — database validation (`get_table_names`, `validate_databases`) and merged-DB queries (`get_all_project_ids`)
- `test_processDataForFig.py` — `get_project_data` / `get_all_data`: query plus valid/error split
- `test_figures.py` — `DataframeForFig`, `Create_Figures`: filtering, rolling statistics, figure/table generation, value formatting
- `test_observer.py` — `myHandler`, `Observer_DBs`, `start_observer`: file-event handling and observer lifecycle

## Fixtures and Test Data

`conftest.py` provides two fixtures:

- `temp_dir` — a throwaway directory, removed after each test
- `test_db_paths` — paths to the pruned SQLite fixtures in the repo root:
  - `list_collect.pruned.sqlite` (MQQC instrument output)
  - `Metadata.pruned.sqlite` (sample / project metadata)

These pruned databases hold anonymized data and are committed, so the suite runs on a
fresh clone with no setup. Tests that need to mutate a fixture copy it into `temp_dir`
first, leaving the committed files read-only.

## What's Covered

- SQLite sync: copy, content preservation, overwrite, missing source, list-length mismatch
- DuckDB full merge and incremental upsert, including column-correct row updates
- Database validation and project-ID querying
- Data filtering, standard-sample removal, rolling statistics
- Figure and table generation, including the empty-data path
- File-system event matching and observer start / stop / partial-failure handling
- Error paths across modules (missing files, failed queries)

Concurrency safety (the single-process DuckDB read/write connection model) and sync crash
atomicity (read-only source + atomic `os.replace`) are covered **by design** rather than by
automated test — both would require real concurrency or a simulated process kill to
exercise meaningfully.

