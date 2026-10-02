# DroneAgent: Decentralized UAV Swarm Framework

A research-grade, fully decentralized framework for autonomous UAV swarms operating in a mesh topology. Each drone runs identical software with behavior determined solely by its configuration file.

## Features

- **Fully Decentralized**: No central controller; each drone makes independent decisions
- **Mesh Topology**: Peer-to-peer UDP communication between neighbors
- **Leaderless**: Emergent behavior through local interactions
- **Multiple Formations**: Line, column, V, diamond, and more
- **Collision Avoidance**: Real-time obstacle and inter-drone collision prevention
- **Mission Execution**: Waypoint following with autonomous takeoff/landing
- **Fault Tolerance**: Automatic neighbor discovery and recovery
- **Safety-Critical**: Pre-flight checks, geofencing, emergency stops
- **Real-World Ready**: Tested in PX4 SITL and ready for Pixhawk 4/Jetson hardware

## Architecture

```
DroneAgent/
├── main.py              # Entry point and thread management
├── config.yaml          # Configuration (the only file that changes per drone)
├── communication.py     # UDP mesh networking
├── packet.py            # Message serialization and validation
├── neighbor.py          # Neighbor discovery and tracking
├── decision.py          # Behavior arbitration
├── formation.py         # Formation geometry
├── planner.py           # Trajectory generation
├── collision.py         # Obstacle avoidance
├── mission.py           # Waypoint management
├── telemetry.py         # MAVSDK telemetry subscription
├── mavsdk_controller.py # Flight control interface
├── state_machine.py     # Drone behavior state machine
├── logger.py            # Comprehensive logging
├── utils.py             # Helper functions
└── requirements.txt     # Python dependencies
```

## Getting Started

### Prerequisites

- Ubuntu 22.04 or 24.04
- Python 3.12
- PX4 Autopilot (for SITL or real hardware)
- MAVSDK-Python

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd DroneAgent
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your drone:
   - Copy the `DroneAgent` folder for each drone in your swarm
   - Edit `config.yaml` for each drone:
     - `drone_id`: Unique integer identifier
     - `vehicle_name`: Optional descriptive name
     - `udp_port`: Communication port (same for all drones)
     - `ip_address`: Usually `0.0.0.0` to listen on all interfaces
     - `neighbor_list`: List of known drone IDs (optional for dynamic discovery)
     - Mission parameters: waypoints, formation, altitude, etc.

### Running in SITL Simulation

1. Start PX4 SITL instance for each drone:
   ```bash
   # For drone 1
   make px4_sitl_default jmavsim
   # Set the appropriate MAVLink UDP port (e.g., 14540 for drone 1)
   
   # For drone 2
   make px4_sitl_default jmavsim
   # Use a different port (e.g., 14550 for drone 2)
   ```

2. Update each drone's `config.yaml` with the correct `mavsdk_connection_url`:
   ```yaml
   mavsdk_connection_url: "udp://:14540"  # For drone 1
   mavsdk_connection_url: "udp://:14550"  # For drone 2
   ```

3. Launch DroneAgent on each companion computer:
   ```bash
   python3 main.py
   ```

### Configuration

All drone behavior is controlled through `config.yaml`. Key sections:

```yaml
drone_id: 1
vehicle_name: "Drone1"
udp_port: 14560
ip_address: "0.0.0.0"
neighbor_list: [2, 3]  # Optional

mission:
  mission_id: 1
  takeoff_altitude: 10.0
  formation: "V"
  waypoint_radius: 2.0
  mission_complete_action: "RTL"
  waypoints:
    - [47.397742, 8.545594, 50.0]
    - [47.397900, 8.545000, 50.0]
    - [47.398000, 8.546000, 50.0]

max_velocity: 5.0      # m/s
max_altitude: 100.0    # meters
safe_distance: 5.0     # meters
heartbeat_rate: 10.0   # Hz
communication_timeout: 1.0  # seconds
```

## Safety Features

- Pre-arm checks (GPS lock, battery, EKF health)
- Geofencing (maximum altitude and distance)
- Collision avoidance with neighboring drones
- Automatic return-to-launch on low battery or signal loss
- Emergency stop capability
- Watchdog timers for communication links

## Communication Protocol

- UDP-based mesh network
- 100ms update rate (configurable)
- Packet structure:
  - Drone ID, timestamp
  - GPS position, local position, velocity
  - Battery, health, mission status
  - Formation index, status flags
  - Packet sequence number, CRC32 checksum
- Duplicate packet detection
- Automatic neighbor discovery and timeout

## Extending the System

To add new formations, modify `formation.py` and add the pattern to `_get_formation_offset`.
To add new behaviors, extend the state machine in `state_machine.py` and the decision engine in `decision.py`.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- PX4 Autopilot Team
- MAVSDK Developers
- Open-source drone research community
