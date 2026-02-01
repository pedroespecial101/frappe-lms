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
log "Waiting for MariaDB..."
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
REDIS_HOST=$(echo $REDIS_CACHE | cut -d: -f1)
REDIS_PORT=$(echo $REDIS_CACHE | cut -d: -f2)
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
 "redis_socketio": "redis://$REDIS_SOCKETIO"
}
EOF

# Create sites/apps.txt if it doesn't exist (required for bench commands)
if [ ! -f sites/apps.txt ]; then
    log "Creating sites/apps.txt..."
    echo "frappe" > sites/apps.txt
fi

# Check if site exists
if [ -d "sites/$SITE_NAME" ]; then
    log "Site $SITE_NAME exists, running migrations..."
    bench --site "$SITE_NAME" migrate
else
    log "Creating new site $SITE_NAME..."
    bench new-site "$SITE_NAME" \
        --mariadb-root-password "$MYSQL_ROOT_PASSWORD" \
        --admin-password "$ADMIN_PASSWORD" \
        --no-mariadb-socket \
        --db-host "$DB_HOST"
    
    log "Installing LMS app..."
    bench --site "$SITE_NAME" install-app lms
    
    log "Setting developer mode..."
    bench --site "$SITE_NAME" set-config developer_mode 1
    
    log "Clearing cache..."
    bench --site "$SITE_NAME" clear-cache
fi

# Build frontend assets (required since removed from Dockerfile)
log "Building frontend assets..."
bench build --app lms

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
