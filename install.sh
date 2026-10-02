#!/bin/bash
set -e

echo "Installing DroneAgent Dependencies..."

# Check OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" = "ubuntu" ] || [ "$ID" = "debian" ] || [ "$ID" = "raspbian" ]; then
        echo "Installing system packages..."
        sudo apt update
        sudo apt install -y python3-pip python3-venv git
    fi
fi

# Setup Venv
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install mavsdk PySide6 pyyaml

echo "Install Complete! Run 'source venv/bin/activate' to start."
