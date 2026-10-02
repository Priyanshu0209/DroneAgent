# DroneAgent Deployment Guide

This guide details the procedure for deploying DroneAgent onto a Raspberry Pi 5 with Pixhawk 4 for real-world autonomous swarm operations.

## Prerequisites
- Raspberry Pi 5 running Ubuntu Server 24.04 (or Raspberry Pi OS 64-bit)
- Pixhawk 4 connected via UART (TELEM2) to Raspberry Pi `/dev/ttyAMA0` (GPIO 14/15)
- WiFi Mesh Network (e.g., BATMAN-adv) assigning static IPs (e.g., `192.168.2.X`)

## 1. Network Configuration
Ensure your swarm is on the same subnet so UDP Broadcast packets (Port 14560) can reach all neighbors.

## 2. Installation
Clone the repository to the Raspberry Pi:
```bash
git clone https://github.com/organization/DroneAgent.git /home/pi/DroneAgent
cd /home/pi/DroneAgent
```

Run the installation script to build the virtual environment and compile the React GUI:
```bash
chmod +x install.sh
./install.sh
```

Ensure your user is part of the `dialout` group to access the Pixhawk serial port:
```bash
sudo usermod -a -G dialout $USER
```

## 3. Configuration
The system uses a layered configuration architecture.
Edit `config/drone1.yaml` (or drone2, drone3) and set your specific IP addresses:

```yaml
drone_id: 1
ip_address: "192.168.2.101"
neighbor_list: [2, 3]
```

Verify `config/real.yaml` points to the correct hardware serial port:
```yaml
connection:
  type: serial
  url: "serial:///dev/ttyAMA0:921600"
```

## 4. Setup Systemd Auto-Start
To ensure DroneAgent starts on boot:
```bash
./setup_systemd.sh
```

## 5. Usage
The service is now running.
- Access the Ground Control GUI via `http://<RPI_IP>:8000`
- Monitor logs: `journalctl -u droneagent -f`
