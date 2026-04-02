#!/bin/bash
# Frappe LMS - unRAID Deployment Script
# Run this script on your unRAID server to deploy the LMS
# Usage: bash deploy_unraid.sh
set -e

echo "================================================"
echo "  Frappe LMS - unRAID Deployment"
echo "================================================"
echo ""

# Configuration
DEPLOY_DIR="/mnt/m2cache/appdata/frappe-lms-repo"
VIDEO_DIR="/mnt/user/mathmo-assets"
APPDATA_DIR="/mnt/m2cache/appdata/frappe-lms"

# Step 1: Check prerequisites
echo "[1/7] Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed. Install Docker from unRAID's Community Applications."
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "ERROR: Docker Compose is not available. Install the Docker Compose plugin."
    exit 1
fi

if [ ! -d "$VIDEO_DIR" ]; then
    echo "WARNING: Video directory $VIDEO_DIR does not exist."
    echo "Videos will not be available until this directory exists."
fi

echo "  Docker: $(docker --version)"
echo "  Compose: $(docker compose version)"
echo ""

# Step 2: Clone or update repo
echo "[2/7] Setting up repository..."
if [ -d "$DEPLOY_DIR" ]; then
    echo "  Repository exists, pulling latest..."
    cd "$DEPLOY_DIR"
    git pull origin develop
else
    echo "  Cloning repository..."
    git clone -b develop https://github.com/pedroespecial101/frappe-lms.git "$DEPLOY_DIR"
    cd "$DEPLOY_DIR"
fi
echo ""

# Step 3: Create .env file
echo "[3/7] Setting up environment..."
if [ ! -f ".env" ]; then
    cp .env.unraid.example .env
    echo "  Created .env from template"
    echo "  ⚠️  IMPORTANT: Edit .env to change MYSQL_ROOT_PASSWORD and ADMIN_PASSWORD!"
else
    echo "  .env already exists, keeping current settings"
fi
echo ""

# Step 4: Create appdata directories
echo "[4/7] Creating persistent data directories..."
mkdir -p "$APPDATA_DIR/db"
mkdir -p "$APPDATA_DIR/redis"
mkdir -p "$APPDATA_DIR/sites"
mkdir -p "$APPDATA_DIR/logs"
echo "  Created directories under $APPDATA_DIR"
echo ""

# Step 5: Build Docker image
echo "[5/7] Building Docker image (this may take 5-15 minutes on first build)..."
docker compose -f docker-compose.unraid.yml build
echo ""

# Step 6: Start the stack
echo "[6/7] Starting Docker Compose stack..."
docker compose -f docker-compose.unraid.yml up -d
echo ""

# Step 7: Wait for health
echo "[7/7] Waiting for services to become healthy..."
echo "  This may take up to 5 minutes on first boot (frontend build + site creation)."
echo "  You can monitor logs with: docker compose -f docker-compose.unraid.yml logs -f lms-app"
echo ""

# Wait for DB first
echo "  Waiting for MariaDB..."
timeout=120
while [ $timeout -gt 0 ]; do
    STATUS=$(docker inspect lms-db --format='{{.State.Health.Status}}' 2>/dev/null || echo "not_running")
    if [ "$STATUS" = "healthy" ]; then
        echo "  ✅ MariaDB is healthy"
        break
    fi
    sleep 5
    timeout=$((timeout - 5))
done

if [ $timeout -le 0 ]; then
    echo "  ❌ MariaDB failed to become healthy. Check: docker logs lms-db"
fi

# Wait for Redis
echo "  Waiting for Redis..."
timeout=60
while [ $timeout -gt 0 ]; do
    STATUS=$(docker inspect lms-redis --format='{{.State.Health.Status}}' 2>/dev/null || echo "not_running")
    if [ "$STATUS" = "healthy" ]; then
        echo "  ✅ Redis is healthy"
        break
    fi
    sleep 5
    timeout=$((timeout - 5))
done

if [ $timeout -le 0 ]; then
    echo "  ❌ Redis failed to become healthy. Check: docker logs lms-redis"
fi

# Wait for App
echo "  Waiting for Frappe LMS app (this takes the longest)..."
timeout=600
while [ $timeout -gt 0 ]; do
    STATUS=$(docker inspect lms-app --format='{{.State.Health.Status}}' 2>/dev/null || echo "not_running")
    if [ "$STATUS" = "healthy" ]; then
        echo "  ✅ Frappe LMS app is healthy!"
        break
    fi
    if [ $((timeout % 30)) -eq 0 ]; then
        echo "  ... still waiting ($((timeout))s remaining, status: $STATUS)"
    fi
    sleep 10
    timeout=$((timeout - 10))
done

if [ $timeout -le 0 ]; then
    echo "  ❌ App failed to become healthy within 10 minutes."
    echo "  Check logs: docker compose -f docker-compose.unraid.yml logs lms-app"
    exit 1
fi

echo ""
echo "================================================"
echo "  🎉 Deployment Complete!"
echo "================================================"
echo ""
echo "  Web UI:  http://$(hostname -I | awk '{print $1}'):9001"
echo "  Login:   Administrator / (password from .env)"
echo "  LMS:     http://$(hostname -I | awk '{print $1}'):9001/lms"
echo ""
echo "  Next steps:"
echo "  1. Login and verify the site works"
echo "  2. Import courses:"
echo "     docker exec lms-app bench --site lms.localhost execute lms.scripts.import_gcse_course.run_import"
echo "  3. Monitor logs:"
echo "     docker compose -f $DEPLOY_DIR/docker-compose.unraid.yml logs -f lms-app"
echo ""
