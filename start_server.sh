#!/bin/bash

# Start dependencies if not running
echo "Checking MariaDB..."
if ! brew services list | grep -q "mariadb.*started"; then
    echo "Starting MariaDB..."
    brew services start mariadb
fi

echo "Checking Redis..."
if ! brew services list | grep -q "redis.*started"; then
    echo "Starting Redis..."
    brew services start redis
fi

# Cleanup existing bench processes
echo "Cleaning up existing processes..."
for PORT in 13000 11000 9000 9001 8000; do
    PID=$(lsof -t -i:$PORT)
    if [ -n "$PID" ]; then
        echo "Killing process on port $PORT (PID: $PID)..."
        kill -9 $PID
    fi
done

# Remove stale PID files that might prevent Redis from restarting
echo "Removing stale PID files..."
rm -f /Users/petetreadaway/Projects/lms-bench/config/pids/*.pid

# Start Bench
echo "Starting Frappe Bench..."
# Use absolute path to ensure we land in the right place regardless of where script is run from
cd /Users/petetreadaway/Projects/lms-bench

# Activate virtual environment to ensure 'bench' command is found
source env/bin/activate

# Run bench start (using honcho directly)
honcho start
