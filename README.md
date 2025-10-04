# ProjectQCDashboard

## Overview
ProjectQCDashboard is a Python/Dash-based dashboard for monitoring mass spectrometry QC data at the project level. It extends [MQQC by Henrik Zauber](https://rdrr.io/rforge/mqqc/man/mqqc-package.html) and my raw2meta project. It is designed for use in our proteomics groups to track instrument performance and sample quality over time.

Instead of showing QC metrics per run, this dashboard aggregates and visualizes them per project, making it easier to spot trends, issues, and outliers across multiple experiments.

It runs in docker and is served via an Apache server and Gunicorn.

## Features
- Monitors MQQC sqlite database and metadata database for changes
- Extracts data from the past two months and write csv files per project with often used QC parameters (Protein IDs, Peptide count, maximum Intensity,Unique Peptide Count, Missed Cleavages %, Maximum pump pressure)
- If enough samples are have been measured (rolling) median and standard deviation are shown

## Quickstart

### Prerequisites
- Python 3.12
- Docker/Podman (recommended for deployment, here I use Podman because of needed licences for Docker)


## Usage
- The dashboard automatically detects changes in the MQQC and metadata database and updates project-level .csvs.
- Select a project from the dropdown to view QC metrics and trends.
- Download csvs for further analysis.
- Export graphs as HTML.

## Configuration
- Main configuration is in `params.yaml` (table names, and monitoring intervals as needed).
- Database and data folders are mounted via Docker Compose; update paths in `.env` for your environment.


#### to do:
- [x] include metadata extracted from raw files and project data
- [x] improve UI
- [x] include tests (started)
- [x] include option to export dashboard as html
- [x] include option to download csv files for further analysis
- [x] add uv.lock file and pyproject.toml
- [x] set up in docker container on server
- [ ] include warning if sample seems to be corrupt
- [ ] choosing project not by dropdown but by entering project ID so also older projects can be looked at
- [ ] include data from LC log
- [ ] clean up code/ more generalized functions
- [ ] give option to comment on project which writes into different database to aggregate information about project for when people leave


#### dependencies:
Uses python 3.12
- dash-bootstrap-components>=2.0.4, flask==3.1.2, gunicorn==23.0.0, numpy==2.3.2, pandas==2.3.2, plotly==6.1.2, pyyaml>=6.0.3, watchdog==6.0.0

## Acknowledgements
- Built on top of [MQQC by Henrik Zauber](https://rdrr.io/rforge/mqqc/man/mqqc-package.html)

#### folder structure:
ProjectFolder_Dashboard/  
├── docker-compose.yml  
├── Dockerfile  
├── list_collect.sqlite (not uploaded due to data privacy)  
├── Metadata.sqlite   (not uploaded due to data privacy)  
├── params.yaml  
├── requirements-docker.txt  
├── WSGI.py  
├── csvFiles/  
├── logs/  
├── .env.example 
├── BuildingContainerDockerCompose.bat (building Docker container with Podman)
├── RestartingContainerDockerCompose.bat (restarting container)
├── xampp-dashboard.conf (Apache config file for dashboard)
├── uv.lock
├── pyproject.toml
├── pytest.ini
└── src/  
&nbsp;└── ProjectQCDashboard/  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── __init__.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── components/  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└──__init__.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── AppLayout.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── GenerateFig.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── SyncDatabases.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── UserInput.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└──config/  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── __init__.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── configuration.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── loadParams.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── logger.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── paths.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── helper/  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── __init__.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── CleanTempCsv.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── common.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── database.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── Figures.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── observer.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── processDataForFig.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── RunningContainer.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── UpdateCSV.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── pipeline/  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└──__init__.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── runApp_local.py  (to run the dahboard locally, not in docker)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── runApp.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── tests/  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└──__init__.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── conftest.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── test_common.py  		  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── test_database_and_updatecsv.py  	
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── test_df_forFigures.py  	