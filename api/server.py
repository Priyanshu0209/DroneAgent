import asyncio
import json
import logging
from typing import List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
import os
import time

logger = logging.getLogger("DroneAgent_API")

app = FastAPI(title="DroneAgent GCS API")

# Global reference to DroneAgent
drone_agent_instance = None

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"GUI Client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"GUI Client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                self.disconnect(connection)

manager = ConnectionManager()

def get_telemetry_payload() -> Dict[str, Any]:
    if not drone_agent_instance:
        return {"error": "DroneAgent not initialized"}
    
    drones_data = []
    
    # 1. Add Local Drone State
    try:
        # Assuming we can get local state from telemetry or state machine
        d_id = drone_agent_instance.config['drone_id']
        local_data = {
            "id": d_id,
            "connected": True,
            "battery": 100.0, # Placeholder
            "mode": "ACTIVE",
            "armed": False,
            "position": {"n": 0, "e": 0, "d": 0},
            "velocity": {"n": 0, "e": 0, "d": 0},
            "heading": 0.0,
            "gps": {"lat": 0, "lon": 0},
            "mission_state": "IDLE"
        }
        drones_data.append(local_data)
    except Exception as e:
        logger.debug(f"Error reading local state: {e}")

    # 2. Add Neighbors State from Mesh Communication
    if hasattr(drone_agent_instance, 'communication'):
        for nid, info in drone_agent_instance.communication.neighbors.items():
            pkt = info.get('last_packet')
            if not pkt: continue
            
            is_active = (time.time() - info['last_heard']) <= drone_agent_instance.communication.communication_timeout
            
            drone_data = {
                "id": pkt.drone_id,
                "connected": is_active,
                "battery": pkt.battery * 100,
                "mode": "GUIDED" if (pkt.status_flags & 0x02) else "UNKNOWN",
                "armed": bool(pkt.status_flags & 0x01),
                "position": {"n": pkt.local_pos_x, "e": pkt.local_pos_y, "d": pkt.local_pos_z},
                "velocity": {"n": pkt.velocity_x, "e": pkt.velocity_y, "d": pkt.velocity_z},
                "heading": pkt.heading * (180/3.14159),
                "gps": {"lat": pkt.gps_lat, "lon": pkt.gps_lon},
                "mission_state": f"Mission {pkt.mission_id}",
            }
            drones_data.append(drone_data)
        
    return {
        "type": "telemetry",
        "formation": "None",
        "drones": drones_data
    }

async def telemetry_broadcaster():
    while True:
        try:
            if manager.active_connections:
                payload = get_telemetry_payload()
                if "error" not in payload:
                    await manager.broadcast(json.dumps(payload))
            await asyncio.sleep(0.1)  # 10Hz
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Telemetry loop error: {e}")
            await asyncio.sleep(1.0)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                cmd_req = json.loads(data)
                cmd = cmd_req.get("command")
                args = cmd_req.get("args", [])
                targets = cmd_req.get("targets", [])
                
                if cmd and drone_agent_instance:
                    logger.info(f"GUI Command received: {cmd} args={args} targets={targets}")
                    
                    # Target filtering
                    is_target = len(targets) == 0 or drone_agent_instance.config['drone_id'] in targets
                    
                    if is_target:
                        # 1. State Machine Commands
                        if cmd == "arm":
                            drone_agent_instance.state_machine.transition('arm_command')
                        elif cmd == "disarm":
                            if drone_agent_instance.backend: drone_agent_instance.backend.disarm()
                        elif cmd == "takeoff":
                            drone_agent_instance.state_machine.transition('takeoff_complete')
                        elif cmd == "land":
                            drone_agent_instance.state_machine.transition('home_reached')
                        elif cmd == "rtl":
                            drone_agent_instance.state_machine.transition('mission_complete')
                        elif cmd == "emergency_stop":
                            drone_agent_instance.state_machine.transition('emergency')
                        
                        # 2. Mission & Planner Commands
                        elif cmd == "pause_mission":
                            # If mission manager supports pause
                            pass
                        elif cmd == "resume_mission":
                            pass
                        elif cmd == "mission_upload":
                            if hasattr(drone_agent_instance.decision_engine, 'update_mission_waypoints'):
                                drone_agent_instance.decision_engine.update_mission_waypoints(args.get('waypoints', []))
                        elif cmd in ["coverage_planner", "search_planner", "scan_planner"]:
                            # Generate waypoints and upload
                            pass
                        
                        # 3. System Commands
                        elif cmd == "shutdown":
                            import os
                            os.system("sudo poweroff")
                        elif cmd == "restart":
                            import os
                            os.system("sudo reboot")
                        elif cmd == "software_update":
                            import os
                            os.system("git pull && ./install.sh")
                            
                        # 4. Parameter Updates
                        elif cmd == "update_parameters":
                            # Apply to global config
                            for k, v in args.items():
                                drone_agent_instance.config[k] = v
                                
                            # Dispatch to specific engines if needed
                            if hasattr(drone_agent_instance.decision_engine, 'update_parameters'):
                                drone_agent_instance.decision_engine.update_parameters(args)
                                
                            if hasattr(drone_agent_instance.communication, 'communication_timeout'):
                                if 'neighbor_timeout' in args:
                                    drone_agent_instance.communication.communication_timeout = args['neighbor_timeout']
                                    
                            if hasattr(drone_agent_instance.heartbeat, 'heartbeat_rate'):
                                if 'heartbeat_rate' in args:
                                    drone_agent_instance.heartbeat.heartbeat_rate = args['heartbeat_rate']
                                    drone_agent_instance.heartbeat.interval = 1.0 / args['heartbeat_rate'] if args['heartbeat_rate'] > 0 else 1.0
                                    
                            if 'logging_level' in args:
                                level_name = args['logging_level'].upper()
                                logging.getLogger().setLevel(getattr(logging, level_name, logging.INFO))
                        
                        # 5. Mouse Flight Controller (Velocity/Position Override)
                        elif cmd == "velocity":
                            # args = {'vx': 1.0, 'vy': 0.0, 'vz': 0.0, 'yaw_rate': 0.0}
                            # Send via backend.set_velocity_ned() directly if in OFFBOARD
                            if drone_agent_instance.backend and drone_agent_instance.state_machine.get_state().name == "OFFBOARD":
                                drone_agent_instance.backend.set_velocity_ned(
                                    args.get('vx', 0), args.get('vy', 0), args.get('vz', 0), args.get('yaw_rate', 0)
                                )

                    await websocket.send_json({"type": "command_result", "command": cmd, "status": "executed"})
            except json.JSONDecodeError:
                logger.error("Invalid JSON from GUI")
            except Exception as e:
                logger.error(f"GUI command error: {e}")
                await websocket.send_json({"type": "error", "message": str(e)})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    logger.info("DroneAgent WebSocket Server Started")
    asyncio.create_task(telemetry_broadcaster())

# Mount Web UI dist folder
web_dist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "dist")
if os.path.exists(web_dist_path):
    app.mount("/", StaticFiles(directory=web_dist_path, html=True), name="static")
else:
    logger.warning(f"Web UI dist folder not found at {web_dist_path}. Run 'npm run build' inside web/")
