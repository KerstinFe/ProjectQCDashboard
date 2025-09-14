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
- Docker/Podman (recommended for deployment)
- Git

## Usage
- The dashboard automatically detects changes in the MQQC and metadata database and updates project-level CSVs.
- Select a project from the dropdown to view QC metrics and trends.
- Download CSVs for further analysis.
- Export graphs as HTML/PDF (only partially impplemented).

## Configuration
- Main configuration is in `params.yaml` (edit paths, table names, and monitoring intervals as needed).
- Database and data folders are mounted via Docker Compose; update paths in `.env` for your environment.


#### to do:
- [x] include metadata extracted from raw files and project data
- [ ] include warning if sample seems to be corrupt
- [ ] improve UI, potentially switching to HoloViz
- [ ] include tests
- [ ] choosing project not by dropdown but by entering project ID so also older projects can be looked at
- [ ] include data from LC log
- [ ] include option to export graphs as pdf
- [x] include option to download csv files for further analysis
- [ ] clean up code, add uv.lock file and pyproject.toml
- [x] set up in docker container on server
- [ ] give option to comment on project which writes into different database to aggregate information about project for when people leave


#### dependencies:
Uses python 3.12
- pandas (V 2.2.3), numpy (V 2.1.3), pythonnet (V 3.0.5) and watchdog (V 6.0.0),  plotly (6.1.2), dash (V 3.0.4), gunicorn (V 23.0.0) to be installed

## Acknowledgements
- Built on top of [MQQC by Henrik Zauber](https://rdrr.io/rforge/mqqc/man/mqqc-package.html)

#### folder structure:
ProjectFolder_Dashboard/  
├── docker-compose.yml  
├── Dockerfile  
├── list_collect.sqlite  
├── Metadata.sqlite  
├── params.yaml  
├── requirements-docker.txt  
├── WSGI.py  
├── csvFiles/  
├── logs/  
├── .env  
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
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── runApp_local.py  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── runApp.py  
		  
