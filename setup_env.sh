#!/bin/bash
set -e

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3.13 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Install the package in editable mode
echo "Installing lms in editable mode..."
pip install -e .

echo "Setup complete! Activate the environment with: source venv/bin/activate"
