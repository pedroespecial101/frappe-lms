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

# Start Bench
echo "Starting Frappe Bench..."
cd ../lms-bench
bench start
