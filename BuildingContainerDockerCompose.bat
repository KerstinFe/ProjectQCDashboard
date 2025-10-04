@echo off

title starting dashboard container with docker compose
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

echo building and starting container....
REM up means it starts  the container, --build that it is forced to build it and -d means it is detached, so no output in the console, runs in background
docker-compose up --build -d

echo container build, window can be closed.
pause

