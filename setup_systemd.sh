#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
SERVICE_FILE="/etc/systemd/system/droneagent.service"

echo "Setting up DroneAgent Systemd Service..."
sudo bash -c "cat > $SERVICE_FILE <<EOF
[Unit]
Description=DroneAgent DroneNode
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$DIR
Environment=PATH=$DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=$DIR/venv/bin/python3 drone_main.py -c config/base.yaml config/network_config.yaml config/real.yaml config/drone1.yaml
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
echo "Service configured. To enable and start:"
echo "sudo systemctl enable droneagent"
echo "sudo systemctl start droneagent"
