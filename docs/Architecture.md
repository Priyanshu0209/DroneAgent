# DroneAgent System Architecture

This document provides visual diagrams of the system architecture, state transitions, and mesh communication protocols.

## System Architecture

```mermaid
graph TD
    DSOS[DSOS / Ground Control Station] <-->|WebSocket| API(FastAPI Server)
    
    API <-->|Commands/Telemetry| Main[main.py]
    
    subgraph DroneAgent Core
        Main --> StateMachine(State Machine)
        Main --> Heartbeat(Heartbeat)
        Main --> Comm(Communication UDP Mesh)
        Main --> Telem(Telemetry)
        Main --> Decision(Decision Engine)
        Main --> Move(Movement Controller)
        
        Decision <-->|Calculates Target| Formation(Formation Logic)
        Decision <-->|Mission Status| Mission(Mission Manager)
        
        Decision --> Move
    end
    
    subgraph Hardware Abstraction Layer
        Move --> Backend{Backend Factory}
        Telem <-- Backend
        StateMachine --> Backend
        
        Backend --> SITL[simulation_backend.py - UDP]
        Backend --> Real[real_backend.py - Serial]
    end
    
    SITL <-->|MAVSDK| PX4_SITL(PX4 SITL / Gazebo)
    Real <-->|MAVSDK| Pixhawk(Pixhawk 4 / Real Hardware)
    
    Comm <..>|UDP Broadcast 14560| OtherDrones(Neighbor Drones)
```

## State Machine Sequence

```mermaid
stateDiagram-v2
    [*] --> BOOT: Power On
    BOOT --> CONNECTING: system_ready
    CONNECTING --> DISCOVERING: backend_connected
    DISCOVERING --> WAITING_MISSION: neighbors_found
    WAITING_MISSION --> READY: mission_received
    
    READY --> ARMING: arm_command
    ARMING --> TAKEOFF: armed
    TAKEOFF --> OFFBOARD: takeoff_complete
    
    OFFBOARD --> FORMATION: formation_ready
    FORMATION --> MISSION: mission_start
    
    MISSION --> RTL: mission_complete
    RTL --> LAND: home_reached
    LAND --> READY: landed
    
    state SafetyFailsafes {
        FAILSAFE
        EMERGENCY
    }
    
    [*] --> EMERGENCY: emergency
    [*] --> FAILSAFE: failsafe
    
    EMERGENCY --> READY: recover
    FAILSAFE --> READY: recover
```

## Communication Sequence (Mesh UDP)

```mermaid
sequenceDiagram
    participant Drone 1
    participant Drone 2
    participant Drone 3
    
    Note over Drone 1: 10Hz Heartbeat Timer
    Drone 1->>Drone 2: UDP Broadcast (ID:1, Pos, Vel, Batt)
    Drone 1->>Drone 3: UDP Broadcast (ID:1, Pos, Vel, Batt)
    
    Note over Drone 2: neighbor.py updates timestamp
    Note over Drone 3: neighbor.py updates timestamp
    
    Note over Drone 2: 10Hz Heartbeat Timer
    Drone 2->>Drone 1: UDP Broadcast (ID:2, Pos, Vel, Batt)
    Drone 2->>Drone 3: UDP Broadcast (ID:2, Pos, Vel, Batt)
    
    Note over Drone 1: Recalculates Formation Centroid
```
