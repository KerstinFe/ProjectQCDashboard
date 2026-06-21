# ProjectQCDashboard - Linux Server Deployment Guide

This guide documents the complete setup for deploying the ProjectQCDashboard Dash application on a Linux server (Kubuntu) using Podman containers and Nginx as a reverse proxy.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Design Decisions](#design-decisions)
3. [Prerequisites](#prerequisites)
4. [Initial Server Setup](#initial-server-setup)
5. [Directory Structure](#directory-structure)
6. [Application Configuration](#application-configuration)
7. [Container Setup](#container-setup)
8. [Systemd Service Configuration](#systemd-service-configuration)
9. [Nginx Reverse Proxy Setup](#nginx-reverse-proxy-setup)
10. [Management Scripts](#management-scripts)
11. [Common Tasks](#common-tasks)
12. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
                                    ┌─────────────────────────────────────────┐
                                    │         Linux Server (Kubuntu)          │
                                    │                                         │
Internet ──► Nginx (ports 80/443) ──┼──► localhost:8050 (Dashboard container) │
             │                      │         │                               │
             │ HTTPS termination    │         ▼                               │
             │ Path: /ProjectQC...  │    Mounted volumes:                     │
             │                      │    - ./logs (read/write)                │
                                    │    - ./data (read/write)                │
                                    │    - external DBs (read-only)           │
                                    │                                         │
                                    │    Runs as user: dashboard              │
                                    │    Managed by: systemd user service     │
                                    └─────────────────────────────────────────┘
```

**Key components:**
- **Nginx**: Handles HTTPS termination and routes `/ProjectQCDashboard/` to the container
- **Podman**: Runs the container rootless (without root privileges) under a service account
- **systemd**: Manages automatic startup and restart of the container
- **Service account `SA`**: Owns the container, allowing multiple admins to manage it

---

## Design Decisions

### Why Nginx instead of Apache?

We chose Nginx because:
- **Simpler configuration** for reverse proxy setups (compare the Nginx config below to the Apache RewriteRule approach)
- **Better documentation** available for this exact use case
- **Lower memory footprint** (minor benefit, but still)
- No institutional requirement for Apache

### Why a shared service account?

We use a dedicated `SA` user because:
- **Containers survive your departure**: Not tied to any individual's account
- **Multiple admins can manage it**: Anyone with sudo access can run commands as this user
- **Security isolation**: Rootless Podman means the container doesn't run as root
- **Clear ownership**: The application belongs to the service account, not a person

### Why systemd user services?

We use systemd because:
- **Standard Linux practice**: Every Linux admin knows systemd commands
- **Automatic restart**: Container restarts on failure and after server reboot
- **Lingering**: Services start at boot without anyone logging into the service account
- **Status and logs**: Built-in commands for monitoring (`systemctl status`, `journalctl`)

### Why path-based routing (`/ProjectQCDashboard/`)?

We use a URL path rather than a subdomain because:
- **Single SSL certificate**: Only one certificate needed for the server
- **Simpler DNS**: No additional DNS records required
- **Matches existing setup**: Consistent with your Windows server configuration

**Trade-off**: The Dash app needs `url-base-pathname` configured (see [Application Configuration](#application-configuration)).

---

## Prerequisites

The server needs:
- Kubuntu (or other Ubuntu-based distribution)
- Internet access (for initial package installation)
- Network access to the database file locations
- SSL certificate (to be provided by institution)

---

## Initial Server Setup

### 1. Install required packages

```bash
# Update package list
sudo apt update

# Install Podman
sudo apt install podman

# Install Nginx
sudo apt install nginx

# Verify installations
podman --version
nginx -v
```

### 2. Create the service account

```bash
# Create user 'SA' with home directory
sudo useradd -m -s /bin/bash SA

# Set a password (needed for initial setup, but won't be used day-to-day)
sudo passwd SA

# Enable lingering - allows user services to run without login
sudo loginctl enable-linger SA
```

### 3. Configure sudo access for admins

Create a sudoers file so authorized users can manage the dashboard without the service account password:

```bash
sudo visudo -f /etc/sudoers.d/SA-admins
```

Add the following (replace `admin1`, `admin2` with actual usernames):

```
# Allow specified users to run commands as 'SA' user 
# Add usernames of admins who need access
admin1 ALL=(SA) NOPASSWD: ALL
admin2 ALL=(SA) NOPASSWD: ALL
```

Now admins can run commands as the SA user:

```bash
# Example: check container status
sudo -iu SA podman ps
```

---

## Directory Structure

All application files live in `/srv/dashboard/`, owned by the `SA` user.
No docker-compose file needed as the systemd file handles this.

```
/srv/dashboard/
├── README.md                    # This documentation
├── app/                         # Application source code
│   ├── src/
│   │   └── ProjectQCDashboard/
│   ├── WSGI.py
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── params.yaml
│   └── *.yml
├── Dockerfile.base              # Base image (dependencies)
├── Dockerfile                   # Application image
├── .env                         # Environment variables
├── logs/                        # Application logs (mounted into container)
├── data/                        # Application data (mounted into container)
├── offline_packages/            # Pre-downloaded Python packages
├── duckdb_extensions/           # DuckDB extensions
├── python-image/                # Saved Python base image
│   └── python-3.12-slim.tar
└── scripts/
    ├── rebuild.sh               # Rebuild and restart container using dashboard-base image
    ├── rebuild-base.sh          # Rebuild dashboard-base image with python and uv installed (without project)
    ├── status.sh                # Check status of container
    ├── start.sh                 # Starting dashboard.service
    ├── stop.sh                  # Stopping dashboard.service
    └── logs.sh                  # View logs
```

### Create the directory structure

```bash
# check if main directory already exists
ls -ld /srv/dashboard

# Create main directory
sudo mkdir -p /srv/dashboard

# Set ownership to SA user
sudo chown -R SA:SA /srv/dashboard

# Create subdirectories (as SA user)
# sudo -iu SA mkdir -p /srv/dashboard/{app,logs,data,scripts,offline_packages,duckdb_extensions,python-image}
sudo -iu SA mkdir -p /srv/dashboard/{app,logs,data}
```

---

## Application Configuration

### 1. Configure `url-base-pathname` in your Dash app

**This is critical for the reverse proxy to work correctly.**

Add `url_base_pathname` as '/ProjectQCDashboard/' to where you create the Dash app (in `AppLayout.py`)
`requests_pathname_prefix` does not work!


```python
# Before (won't work behind reverse proxy with path)
app = Dash(__name__)

# After (works with /ProjectQCDashboard/ path)
app = Dash(
    __name__,
    url_base_pathname='/ProjectQCDashboard/',...
)
```

**Why this is needed**: When Nginx proxies requests to `/ProjectQCDashboard/something`, Dash needs to know that its "root" URL is `/ProjectQCDashboard/`, not `/`. Without this setting, the app generates incorrect URLs for assets and callbacks.

### 2. Create the `.env` file or copy it

Option 1: creating 
```bash
sudo -iu SA nano /srv/dashboard/.env
```

Contents (adjust paths to your actual database locations):

```dotenv
# Database file names (for internal copies)
META_DB_NAME=metadata.sqlite
MQQC_DB_NAME_I1=mqqc.sqlite
MQQC_DB_NAME_I2=mqqc2.sqlite
MERGED_DB_NAME=mergedDB.db

# External database directories (should contain the database files)
MQQC_DB_PATH=/srv/dashboard/data/instrument_1
MQQC_DB_PATH_2=/srv/dashboard/data/instrument_2
METADATA_DB_PATH=/srv/dashboard/data/instrument_3

# Database file names (used to construct full paths)
META_DB_NAME_E=Metadata.sqlite
MQQC_DB_NAME_E1=list_collect.sqlite
MQQC_DB_NAME_E2=list_collect.sqlite
```


Set restrictive permissions:
I did not do this here because there is no sensitive data in the .env file.
```bash
# sudo -iu SA chmod 600 /srv/dashboard/.env
```

### 3. Copy your application code

Copy your application files to `/srv/dashboard/app/`:
You cannot be locked into the server anymore.
Remember to replace **admin@server** 

```bash
cd C:/Path/To/Projectfolder
# From your local machine or wherever the code is
scp -r ./src ./WSGI.py ./pyproject.toml ./uv.lock ./params.yaml ./*.yml admin@server:/tmp/dashboard-app/

# Then on the server, move to final location
sudo cp -r /tmp/dashboard-app/* /srv/dashboard/app/
sudo chown -R SA:SA /srv/dashboard/

# remove what is in the temporary folder so it is not copied into the other folder
sudo rm -rf /tmp/dashboard-app/*

## accordingly also for the dockerfiles but we dont want them to be copied to ./app so we do it seperately.
scp -r  ./Dockerfile ./Dockerfile.base admin@server:/tmp/dashboard-app/

#logged in as admin
sudo cp -r /tmp/dashboard-app/* /srv/dashboard/
sudo chown -R SA:SA /srv/dashboard/
sudo rm -rf /tmp/dashboard-app/*
```


For testing the databases are copied also (as replacement for original databases)
```bash
scp -r ./list_collect.sqlite ./Metadata.sqlite admin@server:/tmp/dashboard-app/

#logged in
sudo mkdir -p  /srv/dashboard/data/original
sudo cp -r /tmp/dashboard-app/* /srv/dashboard/data/original
sudo rm -rf /tmp/dashboard-app/*

#from computer
scp -r ./list_collect.sqlite user@your-server:/tmp/dashboard-app/

#logged in
sudo mkdir -p  /srv/dashboard/data/original2
sudo cp -r /tmp/dashboard-app/* /srv/dashboard/data/original2
sudo chown -R SA:SA /srv/dashboard/
sudo rm -rf /tmp/dashboard-app/* #cleaning up

```


### 4. Copy offline packages and extensions

(Optional, if internet access is not given but then above also the docker files should be copied.)

```bash
# sudo -iu SA cp -r ./offline_packages /srv/dashboard/
# sudo -iu SA cp -r ./duckdb_extensions /srv/dashboard/
# sudo -iu SA cp ./python-image/python-3.12-slim.tar /srv/dashboard/python-image/
```

---

## Container Setup

### 1. Create the Dockerfiles (Optional, if copied above!)

only the dockerfile for online use:
Create `/srv/dashboard/Dockerfile.base`:

```bash
sudo nano /srv/dashboard/Dockerfile.base
```

```dockerfile
FROM python:3.12-slim

# Install uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /ProjectFolder_Dashboard

# Copy only dependency files first for better caching
COPY app/pyproject.toml app/uv.lock ./

# Install dependencies to system Python
RUN --mount=type=cache,target=/root/.cache/uv \
    uv export --frozen --no-dev --no-emit-project -o requirements.txt && \
    uv pip install --system -r requirements.txt
```

Create `/srv/dashboard/Dockerfile`:

```bash
sudo nano /srv/dashboard/Dockerfile
```

```dockerfile
FROM dashboard-base:latest

# Copy the application code
COPY app/src/ ./src/
COPY app/WSGI.py ./
COPY app/params.yaml ./

# Set Python path
ENV PYTHONPATH=/ProjectFolder_Dashboard/src
ENV RUNNING_IN_CONTAINER=true

# Expose port
EXPOSE 8000

# Command to run the application - single worker to prevent duplicate CSV generation
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120", "WSGI:server"]
```

**Note**: Changed port from the conventional 8050 to 8000. Adjust if you prefer 8050.

### 2. Build the images

```bash
# Switch to SA user
sudo -iu SA -i

# Navigate to project directory
cd /srv/dashboard

# Load the Python base image (if using offline approach)
# podman load -i python-image/python-3.12-slim.tar

# Build the base image (only needed when dependencies change)
podman build -t dashboard-base -f Dockerfile.base .

# Build the application image
podman build -t dashboard-app -f Dockerfile .

# Exit back to your user
exit
```

### 3. Test the container manually

```bash
sudo -iu SA bash -c '
  source /srv/dashboard/.env
   podman run -it \
    --name dashboard-test \
    -p 8000:8000 \
    --env-file /srv/dashboard/.env \
    -v /srv/dashboard/logs:/logs:Z \
    -v /srv/dashboard/data:/data:Z \
    -v "${MQQC_DB_PATH}:/external_db_1:ro,Z" \
    -v "${MQQC_DB_PATH_2}:/external_db_2:ro,Z" \
    -v "${METADATA_DB_PATH}:/external_db_3:ro,Z" \
    dashboard-app
  '
```

**Note:** -it means: 
-i: Interactive - keeps stdin open so you can send input to the container
-t: TTY - allocates a terminal, so you see formatted output and can use Ctrl+C

Access `http://server-ip:8000/ProjectQCDashboard/` to verify it works.
http://localhost:8000/ProjectQCDashboard/
Get server ip using `hostname -I` or `ip addr`.

or if the proxy is not set up yet:

```bash
wget -qO- http://localhost:8000/ProjectQCDashboard/
```

Press `Ctrl+C` to stop the test container.

---

## Systemd Service Configuration

### 1. Create the systemd user service

First, ensure the directory exists:

```bash
# check whether it exists
sudo -iu SA ls /home/SA/.config/systemd/user
# create it
sudo -iu SA mkdir -p /home/SA/.config/systemd/user
```

Create the service file:

```bash
sudo -iu SA nano /home/SA/.config/systemd/user/dashboard.service
```

Contents using a wrapper script:

```ini
[Unit]
Description=ProjectQCDashboard Podman Container
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
Restart=always
RestartSec=10
ExecStart=/srv/dashboard/scripts/start-container.sh
ExecStop=/usr/bin/podman stop dashboard
TimeoutStartSec=300
TimeoutStopSec=30

[Install]
WantedBy=default.target
```

**The wrapper script:**

Create `/srv/dashboard/scripts/start-container.sh`:

```bash
sudo -iu SA mkdir -p /srv/dashboard/scripts/
sudo -iu SA nano /srv/dashboard/scripts/start-container.sh
```

Create `/srv/dashboard/scripts/start-container.sh`:

```bash
#!/bin/bash
set -e

# Load environment variables
set -a
source /srv/dashboard/.env
set +a

# Stop and remove existing container (ignore errors if not running)
podman stop dashboard 2>/dev/null || true
podman rm dashboard 2>/dev/null || true

# Start the container
exec podman run \
    --name dashboard \
    -p 8000:8000 \
    --env-file /srv/dashboard/.env \
    -v /srv/dashboard/logs:/logs:Z \
    -v /srv/dashboard/data:/data:Z \
    -v "${MQQC_DB_PATH}:${MQQC_DB1_DIR_CONTAINER}:ro,Z" \
    -v "${MQQC_DB_PATH_2}:${MQQC_DB2_DIR_CONTAINER}:ro,Z" \
    -v "${METADATA_DB_PATH}:${META_DB_DIR_CONTAINER}:ro,Z" \
    dashboard-app
```

**Note about the `:Z` suffix**: This is SELinux labeling. On Ubuntu/Kubuntu (which don't use SELinux by default), it's harmless but ensures compatibility if you later move to RHEL/Rocky Linux.

Make it executable:

```bash
sudo -iu SA chmod +x /srv/dashboard/scripts/start-container.sh
```


### 2. Enable and start the service

```bash
# Reload systemd to pick up new service file
sudo -iu SA XDG_RUNTIME_DIR=/run/user/$(id -u SA) systemctl --user daemon-reload

# Enable the service (start on boot)
sudo -iu SA XDG_RUNTIME_DIR=/run/user/$(id -u SA) systemctl --user enable dashboard.service

# Start the service now
sudo -iu SA XDG_RUNTIME_DIR=/run/user/$(id -u SA) systemctl --user start dashboard.service

# Check status
sudo -iu SA XDG_RUNTIME_DIR=/run/user/$(id -u SA) systemctl --user status dashboard.service
```

**Why `XDG_RUNTIME_DIR`?** When running `systemctl --user` as another user via sudo, systemd needs to know where that user's runtime directory is. This variable tells it.

---

## Nginx Reverse Proxy Setup

### 1. Create the Nginx configuration

```bash
sudo nano /etc/nginx/sites-available/dashboard
```

Contents:

Get Servername using `hostname -f`.

```nginx
# HTTP only (until SSL certificate is provided)
server {
    listen 80;
    server_name your-server.example.com;  # Or your actual hostname

    location /ProjectQCDashboard/ {
        proxy_pass http://127.0.0.1:8000/ProjectQCDashboard/;
        
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (needed for Dash callbacks)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}

```

**OR** 
if ssl certificate is available 

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-server.example.com;  # Replace with your actual hostname
    
    location /ProjectQCDashboard/ {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl;
    server_name your-server.example.com;  # Replace with your actual hostname

    # SSL certificate paths - update these when certificate is provided
    ssl_certificate /etc/ssl/certs/your-certificate.pem;
    ssl_certificate_key /etc/ssl/private/your-certificate-key.pem;

    # SSL configuration (modern settings)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Dashboard application
    location /ProjectQCDashboard/ {
        proxy_pass http://127.0.0.1:8000/ProjectQCDashboard/;
        
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (needed for Dash callbacks)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts (adjust if needed for slow operations)
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

### 2. Enable the site

```bash
# Create symlink to enable the site
sudo ln -s /etc/nginx/sites-available/dashboard /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### 3. Firewall configuration

Firewall configuration is environment-specific. Ensure ports 80 and 443 
are open for incoming traffic.


## Management Scripts

Create these helper scripts in `/srv/dashboard/scripts/` to make common tasks easy.
After creating the scripts, make them executables for usage.

```bash
# create script
sudo nano /srv/dashboard/scripts/scriptname.sh

#change permissions
sudo chown -R SA:SA /srv/dashboard/scripts/

# make it executable
sudo -iu SA chmod +x /srv/dashboard/scripts/*.sh
```
### rebuild.sh

Rebuilds the application image and restarts the container. Use after code changes.

```bash
#!/bin/bash
# /srv/dashboard/scripts/rebuild.sh
# Usage: sudo -iu SA /srv/dashboard/scripts/rebuild.sh

set -e
cd /srv/dashboard

echo "=== Rebuilding dashboard container ==="

echo "Building application image..."
podman build -t dashboard-app -f Dockerfile .

echo "Restarting service..."
XDG_RUNTIME_DIR=/run/user/$(id -u) systemctl --user restart dashboard.service

echo "Waiting for container to start..."
sleep 5

echo "=== Status ==="
XDG_RUNTIME_DIR=/run/user/$(id -u) systemctl --user status dashboard.service --no-pager

echo ""
echo "Done! Dashboard should be available at https://your-server/ProjectQCDashboard/"
```

### rebuild-base.sh

Rebuilds the base image. Use only when dependencies (pyproject.toml) change.

```bash
#!/bin/bash
# /srv/dashboard/scripts/rebuild-base.sh
# Usage: sudo -iu SA /srv/dashboard/scripts/rebuild-base.sh

set -e
cd /srv/dashboard

echo "=== Rebuilding base image (dependencies) ==="
echo "This is only needed when pyproject.toml or uv.lock changes."
echo ""

podman build -t dashboard-base -f Dockerfile.base .

echo ""
echo "Base image rebuilt. Now run rebuild.sh to rebuild the app image."
```

### status.sh

Check the status of the dashboard.

```bash
#!/bin/bash
# /srv/dashboard/scripts/status.sh
# Usage: sudo -iu SA /srv/dashboard/scripts/status.sh

echo "=== Systemd Service Status ==="
XDG_RUNTIME_DIR=/run/user/$(id -u) systemctl --user status dashboard.service --no-pager

echo ""
echo "=== Container Status ==="
podman ps -a --filter name=dashboard

echo ""
echo "=== Recent Logs (last 20 lines) ==="
podman logs --tail 20 dashboard 2>&1 || echo "Container not running"
```

### logs.sh

View container logs.

```bash
#!/bin/bash
# /srv/dashboard/scripts/logs.sh
# Usage: sudo -iu SA /srv/dashboard/scripts/logs.sh [--follow]

if [ "$1" == "--follow" ] || [ "$1" == "-f" ]; then
    podman logs -f dashboard
else
    podman logs --tail 100 dashboard
fi
```

### stop.sh

Stop the dashboard.

```bash
#!/bin/bash
# /srv/dashboard/scripts/stop.sh
# Usage: sudo -iu SA /srv/dashboard/scripts/stop.sh

XDG_RUNTIME_DIR=/run/user/$(id -u) systemctl --user stop dashboard.service
echo "Dashboard stopped."
```

### start.sh

Start the dashboard.

```bash
#!/bin/bash
# /srv/dashboard/scripts/start.sh
# Usage: sudo -iu SA /srv/dashboard/scripts/start.sh

XDG_RUNTIME_DIR=/run/user/$(id -u) systemctl --user start dashboard.service
echo "Dashboard starting..."
sleep 3
XDG_RUNTIME_DIR=/run/user/$(id -u) systemctl --user status dashboard.service --no-pager
```

### Make all scripts executable

```bash
sudo -iu SA chmod +x /srv/dashboard/scripts/*.sh
```

---

## Common Tasks

### View dashboard status

```bash
sudo -iu SA /srv/dashboard/scripts/status.sh
```

### View logs

```bash
# Last 100 lines
sudo -iu SA /srv/dashboard/scripts/logs.sh

# Follow logs in real-time
sudo -iu SA /srv/dashboard/scripts/logs.sh --follow
```

### Restart after code update

1. Copy new code to `/srv/dashboard/app/`
2. Run:
   ```bash
   sudo -iu SA /srv/dashboard/scripts/rebuild.sh
   ```

### Update dependencies

1. Update `offline_packages/` with new packages # not used at the moment because we have internet
2. Update `pyproject.toml` and `uv.lock`
3. Run:
   ```bash
   sudo -iu SA /srv/dashboard/scripts/rebuild-base.sh
   sudo -iu SA /srv/dashboard/scripts/rebuild.sh
   ```

### Stop the dashboard

```bash
sudo -iu SA /srv/dashboard/scripts/stop.sh
```

### Start the dashboard

```bash
sudo -iu SA /srv/dashboard/scripts/start.sh
```

### Check if container restarts after reboot

```bash
# Reboot the server
sudo reboot

# After reboot, check status (no login required - lingering handles this)
sudo -iu SA /srv/dashboard/scripts/status.sh
```

---

## Troubleshooting

### Container won't start

1. Check the logs:
   ```bash
   sudo -iu SA podman logs dashboard
   ```

2. Try running manually to see errors:
   ```bash
   sudo -iu SA /srv/dashboard/scripts/start-container.sh
   ```

3. Verify the image exists:
   ```bash
   sudo -iu SA podman images
   ```

### removing containers and images to restart fresh

can either be done with admin account or using SA account but then the 'sudo -iu SA' has to be left out. 

1. remove container that uses respective image
replace 'dashboard-test' with respective container name
   
```bash
# List all containers (including stopped ones)
sudo -iu SA podman ps -a

# Stop the container if it's running
sudo -iu SA podman stop dashboard-test

# Remove the container
sudo -iu SA podman rm dashboard-test
```

2. remove delete one image or all unused images
   
```bash
# List images
sudo -iu SA podman images

# Remove specific image
sudo -iu SA podman rmi dashboard-app
sudo -iu SA podman rmi dashboard-base

# Or remove all unused images
sudo -iu SA podman image prune -a
```


### "Permission denied" errors

- Check file ownership: `ls -la /srv/dashboard/`
- All files should be owned by `SA:SA`
- Fix with: `sudo chown -R SA:SA /srv/dashboard/`

### Nginx returns 502 Bad Gateway

1. Check if container is running:
   ```bash
   sudo -iu SA podman ps
   ```

2. Check if port 8000 is accessible:
   ```bash
   curl http://localhost:8000/ProjectQCDashboard/
   ```

3. Check Nginx error log:
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

### Dashboard loads but callbacks fail

This usually means `url_base_pathname` is not set correctly. Verify in your Dash app:

```python
app = Dash(__name__, url_base_pathname='/ProjectQCDashboard/')
```

### Database mount errors

1. Verify paths in `.env` are correct
2. Check the paths are accessible from the server
3. Check SELinux/AppArmor aren't blocking (unlikely on Kubuntu)

### Systemd service fails to start at boot

1. Verify lingering is enabled:
   ```bash
   ls /var/lib/systemd/linger/
   # Should show 'SA'
   ```

2. Check service is enabled:
   ```bash
   sudo -iu SA XDG_RUNTIME_DIR=/run/user/$(id -iu SA) systemctl --user is-enabled dashboard.service
   ```

---

## Quick Reference Card

| Task | Command |
|------|---------|
| Check status | `sudo -iu SA /srv/dashboard/scripts/status.sh` |
| View logs | `sudo -iu SA /srv/dashboard/scripts/logs.sh` |
| Follow logs | `sudo -iu SA /srv/dashboard/scripts/logs.sh -f` |
| Restart after code change | `sudo -iu SA /srv/dashboard/scripts/rebuild.sh` |
| Stop dashboard | `sudo -iu SA /srv/dashboard/scripts/stop.sh` |
| Start dashboard | `sudo -iu SA /srv/dashboard/scripts/start.sh` |
| Rebuild base image | `sudo -iu SA /srv/dashboard/scripts/rebuild-base.sh` |
| Enter container shell | `sudo -iu SA podman exec -it dashboard /bin/bash` |
| Check Nginx config | `sudo nginx -t` |
| Reload Nginx | `sudo systemctl reload nginx` |

---

## Files Checklist

Before going live, ensure you have:

- [ ] `/srv/dashboard/.env` with correct database paths
- [ ] `/srv/dashboard/app/` with all application code
- [ ] `/srv/dashboard/Dockerfile` and `Dockerfile.base`
- [ ] `/home/SA/.config/systemd/user/dashboard.service`
- [ ] `/srv/dashboard/scripts/start-container.sh`
- [ ] `/etc/nginx/sites-available/dashboard` (symlinked to sites-enabled)
# - [ ] SSL certificate installed and paths updated in Nginx config
- [ ] `url_base_pathname='/ProjectQCDashboard/'` set in Dash app
- [ ] Lingering enabled for dashboard user
- [ ] Firewall allows ports 80 and 443

If running offline:
- [ ] `/srv/dashboard/offline_packages/` with Python packages
- [ ] `/srv/dashboard/duckdb_extensions/` with DuckDB extension

---

*Last updated: 2026-06-18*

