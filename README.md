# ProjectQCDashboard
Add on to the [MQQC by Henrik Zauber](https://rdrr.io/rforge/mqqc/man/mqqc-package.html) in our institute. QC data is not shown per run but per project to monitor mass spec performance during the measurements.

#### features: 
- Monitors MQQC sqlite database for changes
- Extracts data from the past two months and write csv files per project with often used QC parameters (Protein IDs, Peptide count, maximum Intensity,Unique Peptide Count, Missed Cleavages %)
- if enough samples are have been measured (rolling) median and standard deviation are shown

#### to do:
- [ ] include metadata extracted from raw files and project data
- [ ] include warning if sample seems to be corrupt
- [ ] choosing project not by dropdown but by entering project ID so also older projects can be looked at
- [ ] include data from LC log
- [ ] include option to export graphs as html/pdf
- [ ] include option to download csv files for further analysis
- [ ] clean up code and make it more generic
- [ ] set up in docker container on server
- [ ] give option to comment on project which writes into different database to aggregate information about project for when people leave


#### dependencies:
Uses python 3.12
- pandas (V 2.2.3), numpy (V 2.1.3), pythonnet (V 3.0.5) and watchdog (V 6.0.0),  plotly (6.1.2), dash (3.0.4) to be installed

  
 
#### folder structure:
ProjectQCDashboard/  
├── csv_files/  
│   
 
  


