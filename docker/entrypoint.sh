#!/bin/bash
# Frappe LMS Docker Entrypoint - Idempotent Site Initialization
set -e

# Defaults
SITE_NAME=${SITE_NAME:-lms.localhost}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin}
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-frappe123}
DB_HOST=${DB_HOST:-lms-db}
REDIS_CACHE=${REDIS_CACHE:-lms-redis:6379/0}
REDIS_QUEUE=${REDIS_QUEUE:-lms-redis:6379/1}
REDIS_SOCKETIO=${REDIS_SOCKETIO:-lms-redis:6379/2}

# Environment Setup for Frappe and Node
export NVM_DIR="/home/frappe/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
export PATH="/home/frappe/.local/bin:/home/frappe/.nvm/versions/node/v${NODE_VERSION:-20.19.2}/bin:$PATH"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Trap SIGTERM for graceful shutdown
cleanup() {
    log "Received SIGTERM, shutting down gracefully..."
    kill -TERM $SOCKETIO_PID $WORKER_PID $SCHEDULER_PID 2>/dev/null || true
    wait
    exit 0
}
trap cleanup SIGTERM SIGINT

# Wait for MariaDB
log "Waiting for MariaDB at $DB_HOST..."
timeout=60
while ! mysqladmin ping -h"$DB_HOST" -uroot -p"$MYSQL_ROOT_PASSWORD" --silent 2>/dev/null; do
    timeout=$((timeout - 1))
    if [ $timeout -le 0 ]; then
        log "ERROR: MariaDB not ready after 60s"
        exit 1
    fi
    sleep 1
done
log "MariaDB ready"

# Wait for Redis
log "Waiting for Redis..."
# Parse Redis host and port from REDIS_CACHE (format: host:port/db)
REDIS_HOST=$(echo $REDIS_CACHE | cut -d: -f1)
REDIS_PORT=$(echo $REDIS_CACHE | cut -d: -f2 | cut -d/ -f1)
timeout=30
while ! redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" PING >/dev/null 2>&1; do
    timeout=$((timeout - 1))
    if [ $timeout -le 0 ]; then
        log "ERROR: Redis not ready after 30s"
        exit 1
    fi
    sleep 1
done
log "Redis ready"

# Configure common_site_config.json directly
log "Configuring common_site_config..."
cd /home/frappe/frappe-bench
cat > sites/common_site_config.json <<EOF
{
 "db_host": "$DB_HOST",
 "redis_cache": "redis://$REDIS_CACHE",
 "redis_queue": "redis://$REDIS_QUEUE",
 "redis_socketio": "redis://$REDIS_SOCKETIO",
 "is_single_site": 1
}
EOF

# Create sites/apps.txt with both frappe and lms
log "Creating sites/apps.txt..."
echo -e "frappe\nlms" > sites/apps.txt

# Check if site exists
if [ -d "sites/$SITE_NAME" ]; then
    log "Site $SITE_NAME exists, running migrations..."
    bench --site "$SITE_NAME" migrate
    bench use "$SITE_NAME"
else
    log "Creating new site $SITE_NAME..."
    bench new-site "$SITE_NAME" \
        --mariadb-root-password "$MYSQL_ROOT_PASSWORD" \
        --admin-password "$ADMIN_PASSWORD" \
        --no-mariadb-socket \
        --db-host "$DB_HOST" \
        --mariadb-user-host-login-scope='%'
    
    log "Installing LMS app..."
    bench --site "$SITE_NAME" install-app lms
    
    log "Setting developer mode..."
    bench --site "$SITE_NAME" set-config developer_mode 1
    
    log "Setting default site..."
    bench use "$SITE_NAME"
    
    log "Clearing cache..."
    bench --site "$SITE_NAME" clear-cache
fi

# Ensure site symlinks for hostname resolution (prevents 404 "Not Found" for Host header)
log "Ensuring site symlinks for hostname resolution..."
for host in "localhost" "127.0.0.1" "optiplex3070-1" "$(hostname)"; do
    if [ ! -e "sites/$host" ]; then
        ln -sf "$SITE_NAME" "sites/$host"
    fi
done

# Create video symlinks from /app/videos to public/files
# This makes videos accessible via /files/filename.mp4 through the custom video.py endpoint
if [ -d "/app/videos" ]; then
    log "Creating video symlinks from /app/videos to public/files..."
    SITE_FILES="sites/$SITE_NAME/public/files"
    mkdir -p "$SITE_FILES"
    
    VIDEO_COUNT=0
    for video in /app/videos/*.mp4; do
        if [ -f "$video" ]; then
            basename=$(basename "$video")
            if [ ! -e "$SITE_FILES/$basename" ]; then
                ln -s "$video" "$SITE_FILES/$basename"
            fi
            VIDEO_COUNT=$((VIDEO_COUNT + 1))
        fi
    done
    log "Linked $VIDEO_COUNT video files"
else
    log "WARNING: /app/videos not mounted, skipping video symlinks"
fi

# Frontend build at runtime if assets are missing or incomplete
# This avoids OOM during Docker build on resource-constrained servers
if [ ! -d "apps/lms/lms/public/dist" ] || [ -z "$(find apps/lms/lms/public/dist -name "*.css" 2>/dev/null)" ]; then
    log "Frontend assets missing or incomplete, building apps (this may take several minutes)..."
    export NODE_OPTIONS="--max-old-space-size=4096"
    export PATH=$PATH:$(pwd)/apps/lms/frontend/node_modules/.bin
    bench build --app lms --app frappe
    bench --site "$SITE_NAME" clear-cache
fi

log "Starting services..."

# Start SocketIO in background
node apps/frappe/socketio.js &
SOCKETIO_PID=$!
log "SocketIO started (PID: $SOCKETIO_PID)"

# Start Worker in background
bench worker --queue default,short,long &
WORKER_PID=$!
log "Worker started (PID: $WORKER_PID)"

# Start Scheduler in background
bench schedule &
SCHEDULER_PID=$!
log "Scheduler started (PID: $SCHEDULER_PID)"

# Start web server in foreground (PID 1)
log "Starting web server on port 9001..."
exec bench serve --port 9001
