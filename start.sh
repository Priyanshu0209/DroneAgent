#!/bin/bash
# DroneAgent Startup Script

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "Starting DroneAgent..."

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run ./install.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Use provided arguments as configs, or default to simulation and drone1
CONFIGS=$@
if [ -z "$CONFIGS" ]; then
    CONFIGS="config/base.yaml config/simulation.yaml config/drone1.yaml"
    echo "No config provided. Defaulting to: $CONFIGS"
fi

# Run main application
python3 main.py -c $CONFIGS
