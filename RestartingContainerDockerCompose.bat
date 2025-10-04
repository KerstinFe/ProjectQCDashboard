@echo off

title restarting dashboard container without rebuilding the image
echo Starting dashboard container...
echo Press Ctrl+C to stop
echo ================================

set "PROJECT_DIR=%~dp0"
REM Remove trailing backslash
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

REM Change to project directory
cd /d "%PROJECT_DIR%"

echo Project directory: %PROJECT_DIR%
echo Current directory: %cd%

echo starting container....
REM up: starting, --no-build: what it says, -d: detached, no output in console shown
docker-compose up --no-build -d dashboard

echo container build, window can be closed.
pause

