# DroneAgent WebSocket API Documentation

## Connection
**Endpoint**: `ws://<DroneAgent-IP>:8000/ws`
**Format**: JSON

## Server -> Client (Downlink)

### Telemetry Update
Broadcast at 10Hz containing the state of the local drone and all its active neighbors.
```json
{
  "type": "telemetry",
  "formation": "V",
  "drones": [
    {
      "id": 1,
      "connected": true,
      "battery": 95.5,
      "mode": "ACTIVE",
      "armed": true,
      "position": {"n": 0, "e": 0, "d": -10},
      "velocity": {"n": 5, "e": 0, "d": 0},
      "heading": 45.0,
      "gps": {"lat": 47.3977, "lon": 8.5455},
      "mission_state": "Mission 1"
    }
  ]
}
```

## Client -> Server (Uplink)

### Send Command
Send commands to specific drones or the entire swarm. If `targets` is empty `[]`, it applies to all drones.

```json
{
  "command": "arm",
  "targets": []
}
```

**Available Commands**:
- `arm`
- `disarm`
- `takeoff`
- `land`
- `rtl`
- `emergency_stop`

### Live Parameter Override
Dynamically tune flight parameters without restarting the process.
```json
{
  "command": "update_formation",
  "args": {
    "formation": "diamond",
    "formation_spacing": 15.0,
    "max_velocity": 8.0
  },
  "targets": []
}
```

### Virtual Flight Controller Override
Takes over manual velocity setpoints when the drone is in `OFFBOARD` mode.
```json
{
  "command": "velocity",
  "args": {
    "vx": 2.0,
    "vy": 0.0,
    "vz": -0.5,
    "yaw_rate": 15.0
  },
  "targets": [1]
}
```
