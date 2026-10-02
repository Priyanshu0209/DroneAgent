# Developer Guide: DroneAgent Backend

## Architecture
DroneAgent is built around a single-binary, multi-threaded python architecture that utilizes a Factory Pattern for abstracting Hardware (PX4 / SITL) from Business Logic.

### Layers
1. **Application Layer (`main.py`)**: Entry point that loads configuration, initializes the FastAPI server, and spawns subsystem threads.
2. **Behavior Layer**:
   - `decision.py`: Time-based dynamic target selection, finite-state triggers.
   - `formation.py`: 24 geometric mathematical swarm topologies using leaderless consensus.
   - `mission.py`: Sequential waypoint navigation.
3. **Execution Layer**:
   - `movement_controller.py`: Computes local proportional control to execute the target setpoints sent by `decision.py`.
   - `state_machine.py`: Manages strict behavioral transitions (READY -> ARM -> TAKEOFF -> OFFBOARD).
4. **Communication Layer**:
   - `communication.py`: UDP broadcast mesh with duplicate detection, queueing, and timeouts.
   - `packet.py`: Custom struct-packed binary frames with CRC32.
   - `heartbeat.py` & `neighbor.py`: Tracks neighbor liveness and triggers failsafes.
5. **Hardware Abstraction Layer (HAL)**:
   - `backend.py` (Abstract Interface)
   - `simulation_backend.py` (MAVSDK SITL)
   - `real_backend.py` (MAVSDK Serial)

## Development Workflow
1. Develop using `python3 main.py -c config/base.yaml config/simulation.yaml config/drone1.yaml`.
2. Do not modify `MAVSDK` or `PX4` C++ internals.
3. Test mesh reliability by running multiple instances with different `drone_id` config files on the same host (UDP ports must be distinct if on same host, but for real deployment they use 14560 on different IPs).
