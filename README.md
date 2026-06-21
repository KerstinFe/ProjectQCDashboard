# ProjectQCDashboard
 
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
 
An interactive quality control dashboard for mass spectrometry proteomics data. Built on top of [MQQC by Henrik Zauber](https://rdrr.io/rforge/mqqc/man/mqqc-package.html), this dashboard aggregates and visualizes QC metrics **per project** rather than per run, making it easier to spot trends, issues, and outliers across multiple experiments over time.
 
## Background
 
MQQC produces per-run QC metrics stored in a SQLite database. This dashboard consumes that database alongside a metadata database (from a companion raw2meta pipeline) and merges them into a unified DuckDB store. The result is a project-level view of instrument performance and sample quality, served as an interactive Dash web application inside a Podman container.
 
## Features
 
- **Real-time monitoring**: Watches MQQC and metadata databases for changes via file system polling and syncs automatically
- **Multi-instrument support**: Handles multiple MQQC databases and merges them into a unified view
- **Interactive visualizations**: Scatter plots with rolling median/standard deviation trend lines (switches to static median for smaller datasets)
- **Project-based filtering**: Select any project from a dropdown to view its QC metrics
- **Error tracking**: Dedicated table for files with processing issues
- **Export**: Download project data as CSV or export the full dashboard view as a standalone HTML report
- **Container-ready**: Designed for rootless Podman deployment with Nginx as reverse proxy and systemd for service management
## Architecture
 
### Architecture Decisions
 
**Single Gunicorn worker**
This dashboard is designed for internal lab use with a small number of concurrent users. A single worker simplifies state management: the DB version counter, cache, and background threads (file observer, queue 
processor) all live in the same process without requiring inter-process coordination. For deployments with higher concurrent load, the background threads should be extracted into a separate systemd service, and the 
in-process version counter replaced with a shared signal (e.g. `meta_data` table in DuckDB). 
 
**No async**
Although Dash supports async, the small number of concurrent users, and DuckDBs synchronous set up, the usage of threads is sufficient at the scale of this project.  
 
 
![flowchart](/image/260618_FlowDiagram.png)
 
```
├── README.md                           # This documentation
├── src/                                # Application source code
│   └── ProjectQCDashboard/
│       ├── ui/                         # Dash layout, callbacks and visualizations
│       │   ├── AppLayout.py            # Dash app layout and callbacks
│       │   ├── AppLayoutComponents.py  # UI component helpers and figure orchestration
│       │   ├── Figures.py              # Figure generation logic
│       │   └── processDataForFig.py    # Data retrieval and preprocessing
│       ├── background/                 # Background processes
│       │   ├── observer.py             # File system monitoring for DB changes
│       │   └── processQ.py             # Queue processor and debounce logic
│       ├── db/                         # Database interaction
│       │   ├── database.py             # DuckDB query helpers and version cache
│       │   ├── SyncDatabases.py        # SQLite database synchronisation
│       │   ├── UpdateDB.py             # DuckDB merge and incremental update logic
│       │   └── ValidateDatabases.py    # Startup database validation
│       ├── config/                     # Configuration management
│       │   ├── schemas.py              # Pydantic model schemas
│       │   ├── configuration.py        # Parsed application settings
│       │   ├── loadParams.py           # YAML parameter loading with Pydantic validation
│       │   ├── logger.py               # Logging setup
│       │   ├── paths.py                # Path resolution (container vs. local)
│       │   └── RunningContainer.py     # Container environment detection
│       └── pipeline/                   # Entry points
│           └── runApp.py               # Application entry point for both container and local development
├── TestData/                           # Example SQLite input data for local testing
│   ├── list_collect.pruned.sqlite
│   ├── list_collect.pruned_new.sqlite  # has two rows more, to test observer & updating 
│   ├── Metadata.pruned.sqlite
│   └── Metadata.pruned_new.sqlite      # has two rows more, to test observer & updating 
├── tests/                              # pytest test suite
├── WSGI.py
├── pyproject.toml
├── uv.lock
├── params.yaml                         # Runtime parameters (polling interval, thresholds, plot config)
├── Dockerfile.base                     # Base image (dependencies)
├── Dockerfile                          # Application image
├── .env                                # Environment variables
├── logs/                               # Application logs (mounted into container)
└── scripts/
    ├── rebuild.sh                      # Rebuild and restart container using dashboard-base image
    ├── rebuild-base.sh                 # Rebuild dashboard-base image with python and uv installed (without project)
    ├── status.sh                       # Check status of container
    ├── start.sh                        # Starting dashboard.service
    ├── stop.sh                         # Stopping dashboard.service
    └── logs.sh                         # View logs
```
 
### Data Flow
 
1. **Detection**: File system observers poll external MQQC and metadata SQLite databases for changes
2. **Sync**: Modified databases are copied to internal writable storage
3. **Merge**: DuckDB performs a full join across all MQQC and metadata sources into a single `project_data` table
4. **Visualise**: Dash renders interactive scatter plots and summary tables per project
5. **Export**: Users download CSV data or a self-contained HTML snapshot
## Installation
 
### Requirements
 
- Python 3.12+
- Podman or Docker (for container deployment), I chose Podman because of needed licences for Docker


### Local Development Setup
 
1. Clone the repository:
```bash
git clone https://github.com/KerstinFe/ProjectQCDashboard.git
cd ProjectQCDashboard
```
 
2. Install dependencies:
```bash
uv sync
```
 
3. Copy `.env.example` to `.env.dev` and fill in your database filenames:
```bash
cp .env.example .env
```
 
4. Run the local development server:
```bash
python -m ProjectQCDashboard.pipeline.runApp
```
 
5. Access the dashboard at `http://localhost:8050/ProjectQCDashboard/`

### Container Deployment
 
See [dash-deployment-guide.md](dash-deployment-guide.md) for the full guide covering Podman, Nginx, and systemd setup.
 
Quick start:
```bash
./scripts/start-container.sh
```
 
The application will be available at `http://localhost:8000/ProjectQCDashboard/`
 
## Configuration
 
### Environment Variables (`.env`)
 
See `.env.example` for a full template. Variables are grouped by purpose:
 
**External database paths (host filesystem mount points):**
 
| Variable | Description |
|----------|-------------|
| `MQQC_DB_PATH` | Host path to the directory containing the primary MQQC database |
| `MQQC_DB_PATH_2` | Host path to the directory containing the secondary MQQC database (optional) |
| `METADATA_DB_PATH` | Host path to the directory containing the metadata database |
 
**External database filenames (original source files):**
 
| Variable | Description | Example |
|----------|-------------|---------|
| `MQQC_DB_NAME_E1` | Primary MQQC database filename on host | `MQQC_1.sqlite` |
| `MQQC_DB_NAME_E2` | Secondary MQQC database filename on host (optional) | `MQQC_2.sqlite` |
| `META_DB_NAME_E` | Metadata database filename on host | `original_Metadata.sqlite` |
 
**Container-internal paths:**
 
| Variable | Description | Default |
|----------|-------------|---------|
| `MQQC_DB1_DIR_CONTAINER` | Mount point for primary MQQC database inside container | `/external_db_1` |
| `MQQC_DB2_DIR_CONTAINER` | Mount point for secondary MQQC database inside container (optional) | `/external_db_2` |
| `META_DB_DIR_CONTAINER` | Mount point for metadata database inside container | `/external_db_3` |
 
**Internal database filenames (working copies inside container):**
 
| Variable | Description | Default |
|----------|-------------|---------|
| `MQQC_DB_NAME_I1` | Primary MQQC working copy filename | `MQQC_1.sqlite` |
| `MQQC_DB_NAME_I2` | Secondary MQQC working copy filename (optional) | — |
| `META_DB_NAME` | Metadata working copy filename | `Metadata.sqlite` |
| `MERGED_DB_NAME` | Output merged DuckDB filename | `mergedDB.db` |
 
### Parameters (`params.yaml`)
 
| Parameter | Description | Default |
|-----------|-------------|---------|
| `ThresholdForRollingMean` | Minimum samples before switching to rolling statistics | `30` |
| `ThresholdForTwoColumnsOfGraphs` | Row count above which graphs switch to single-column layout | `75` |
| `UpdateLastXEntries` | Number of recent entries processed on incremental DB update | `500` |
| `PollingIntervalSeconds` | File system polling interval in seconds | `60` |
 
The `PLOT_CONFIG` section of `params.yaml` controls which QC metrics are shown, in what order, and under what labels — no code changes needed to add or remove plots.
 
## Testing
 
```bash
# Run all tests
pytest
 
# Or specific test file
pytest tests/test_figures.py -v
```
 
See [tests/README.md](tests/README.md) for details.
 
## To Do
 
Will potentially be added in the future:
- [ ] Incorporate LC log data

## Acknowledgements
 
- [MQQC by Henrik Zauber](https://rdrr.io/rforge/mqqc/man/mqqc-package.html) — the underlying QC metric engine this dashboard visualises
