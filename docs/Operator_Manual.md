# DroneAgent Operator Manual

This manual details how to operate the Drone Swarm via the Glassmorphism Ground Control Station (GCS).

## GCS Layout

### Top Bar
- **Global Commands**: Use these buttons to `Arm All`, `Takeoff All`, or `Land All` drones simultaneously.
- **Mission Controls**: Start, Pause, or Resume the autonomous swarm mission.
- **Mesh Status**: Quickly view the health of the UDP mesh communication link.

### Center Panel (Interactive Map)
- **Map View**: Displays the live position, GPS trails, and telemetry vectors of all active drones.
- **Mouse Flight Controller**: A transparent overlay allows you to command the swarm using on-screen virtual joysticks or click-to-go capabilities.

### Left Panel (Mission Editor)
- **Coverage Planner**: Automatically generate grid-coverage waypoint missions for selected drones.
- **Waypoint Editor**: Add, modify, or delete waypoints. Click "Upload" to distribute to the swarm.

### Right Panel (Telemetry & Tuning)
- **Drone Selection**: Click a drone card (e.g., Drone 1) to isolate telemetry data and send commands ONLY to that drone.
- **Live Parameters**: Adjust Cruise Speed, Max Altitude, and Formation Spacing in real-time. The swarm will immediately recalculate its dynamic formations.

## Keyboard Shortcuts
- **W, A, S, D**: Move selected drone(s) North, West, South, East.
- **Q, E**: Rotate Yaw Left / Right.
- **Space / Ctrl+Space**: Altitude Up / Down.
- **R**: Return to Launch (RTL).
- **L**: Land.
- **Esc**: Emergency Stop / Kill Switch.

## Formations
Select from 24 unique formations (Line, V, Diamond, Arc, Spiral, etc.). As the swarm flies, if a drone is lost or fails, the remaining drones will automatically recalculate the formation center and re-align in the air without operator intervention.
