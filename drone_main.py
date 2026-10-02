#!/usr/bin/env python3
"""
DroneAgent Main Entry Point

Initializes and coordinates all subsystems:
- Communication
- Heartbeat
- Telemetry
- Decision
- Planner
- Movement
- Mission
- Logging

Handles startup and shutdown sequences.
"""

import threading
import signal
import sys
import time
from typing import Dict, Any
import argparse
from config import load_config, ConfigurationError
from backend_factory import BackendFactory

# Import local modules
from communication import Communication
from heartbeat import Heartbeat
from telemetry import Telemetry
from decision import DecisionEngine
from planner import Planner
from movement_controller import MovementController
from mission import MissionManager
from logger import DroneLogger
from state_machine import StateMachine

class DroneAgent:
    def __init__(self, config_paths: list):
        """
        Initialize the DroneAgent with configuration.
        
        Args:
            config_paths: List of paths to configuration YAML files
        """
        self.config = self._load_config(config_paths)
        self.logger = DroneLogger(self.config.get('drone_id', 1)).get_logger()
        
        # Initialize subsystems
        self.backend = BackendFactory(self.config, self.logger)
        self.communication = Communication(self.config, self.logger)
        self.telemetry = Telemetry(self.config, self.logger, backend=self.backend)
        self.state_machine = StateMachine(
            self.config, self.logger,
            backend=self.backend,
            telemetry=self.telemetry,
            communication=self.communication
        )
        self.mission_manager = MissionManager(self.config, self.logger)
        self.decision_engine = DecisionEngine(self.config, self.logger)
        self.planner = Planner(self.config, self.logger)
        self.movement_controller = MovementController(
            self.config, self.logger,
            backend=self.backend,
            decision_engine=self.decision_engine,
            state_machine=self.state_machine,
            planner=self.planner,
            telemetry=self.telemetry
        )
        self.heartbeat = Heartbeat(
            self.config, self.logger,
            communication=self.communication,
            telemetry=self.telemetry,
            state_machine=self.state_machine
        )
        
        # Thread management
        self.threads: Dict[str, threading.Thread] = {}
        self.shutdown_event = threading.Event()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.logger.info("DroneAgent initialized")
    
    def _load_config(self, config_paths: list) -> Dict[str, Any]:
        """Load configuration from YAML files."""
        try:
            config = load_config(config_paths)
            # Add some derived configurations
            config['heartbeat_rate'] = config.get('heartbeat_rate', 10)  # Hz
            config['communication_timeout'] = config.get('communication_timeout', 1.0)  # seconds
            config['safe_distance'] = config.get('safe_distance', 5.0)  # meters
            return config
        except ConfigurationError as e:
            print(f"ConfigurationError: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Failed to load config: {e}")
            sys.exit(1)
    
    def start(self):
        """Start all subsystems."""
        self.logger.info("Starting DroneAgent...")
        
        # Start Backend first and ensure it succeeds
        if not self.backend.connect():
            self.logger.error("Backend connection failed. Exiting.")
            sys.exit(1)
            
        # At this point, MAVSDK is fully connected and initialized
        
        # Start telemetry using MAVSDK's event loop
        self.telemetry.start()
        
        # Start Mesh Communication
        self.communication.start()
        threading.Thread(target=self.communication.transmit_loop, daemon=True, name="CommTx").start()
        threading.Thread(target=self.communication.receive_loop, daemon=True, name="CommRx").start()
        
        # Start Mission
        if hasattr(self, 'mission_manager') and hasattr(self.mission_manager, 'start'):
            self.mission_manager.start()
            
        # Start Planner (if applicable)
        if hasattr(self, 'planner') and hasattr(self.planner, 'start'):
            self.planner.start()
        
        # Start Decision Engine
        self.decision_engine.start()
        
        # Start Formation (handled by movement controller/decision)
        if hasattr(self, 'formation') and hasattr(self.formation, 'start'):
            self.formation.start()
            
        # Start Collision Avoidance
        if hasattr(self, 'collision_avoidance') and hasattr(self.collision_avoidance, 'start'):
            self.collision_avoidance.start()

        # Start State Machine, Movement, Heartbeat
        threading.Thread(target=self.state_machine.update_loop, daemon=True, name="StateMachine").start()
        self.movement_controller.start()
        self.heartbeat.start()
        
        self.logger.info("All subsystems started")
        
        # Start command processor loop for GCS commands
        threading.Thread(target=self.command_processor_loop, daemon=True, name="CmdProcessor").start()

        # Drone runs headlessly
        self.logger.info("DroneNode running headlessly.")
        try:
            while not self.shutdown_event.is_set():
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        finally:
            self.shutdown()
    
    def command_processor_loop(self):
        """Listen to recv_queue for CommandPackets from GCS."""
        from packet import CommandPacket
        while not self.shutdown_event.is_set():
            packet_tuple = self.communication.get_received_packet(timeout=0.5)
            if packet_tuple:
                packet, addr = packet_tuple
                if isinstance(packet, CommandPacket):
                    self.execute_command(packet)
                    
    def execute_command(self, packet):
        self.logger.info(f"Executing GCS command: {packet.command} with args: {packet.args}")
        try:
            cmd = packet.command
            args = packet.args
            
            if cmd == 'arm':
                self.backend.arm()
            elif cmd == 'disarm':
                self.backend.disarm()
            elif cmd == 'takeoff':
                self.backend.takeoff(args.get('alt', 10.0))
            elif cmd == 'land':
                self.backend.land()
            elif cmd == 'rtl':
                self.backend.return_to_launch()
            elif cmd == 'pause':
                self.backend.pause()
            elif cmd == 'resume':
                self.backend.resume()
            elif cmd == 'kill':
                self.backend.emergency_stop()
            elif cmd == 'transition':
                self.state_machine.transition(args.get('state'))
            elif cmd == 'upload_mission':
                self.mission_manager.upload_mission(args.get('waypoints', []))
            elif cmd == 'cancel_mission':
                self.mission_manager.cancel_mission()
            elif cmd == 'move':
                if hasattr(self.movement_controller, 'set_manual_velocity'):
                    self.movement_controller.set_manual_velocity(
                        args.get('vx', 0.0), args.get('vy', 0.0), args.get('vz', 0.0), args.get('yaw', 0.0)
                    )
            elif cmd == 'set_offboard_mode':
                if hasattr(self.backend, 'set_offboard_mode'):
                    self.backend.set_offboard_mode()
            elif cmd == 'offboard_stop':
                if hasattr(self.backend, 'offboard_stop'):
                    self.backend.offboard_stop()
            elif cmd == 'hover':
                self.state_machine.transition('OFFBOARD')
                if hasattr(self.movement_controller, 'set_manual_velocity'):
                    self.movement_controller.set_manual_velocity(0.0, 0.0, 0.0, 0.0)
            elif cmd == 'formation':
                self.state_machine.transition('FORMATION')
            elif cmd == 'mission':
                self.state_machine.transition('MISSION')
            else:
                self.logger.warning(f"Unknown command received: {cmd}")
        except Exception as e:
            self.logger.error(f"Error executing command {packet.command}: {e}")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown()
    
    def shutdown(self):
        """Gracefully shut down all subsystems."""
        self.logger.info("Shutting down DroneAgent...")
        self.shutdown_event.set()
        
        self.heartbeat.stop()
        self.movement_controller.stop()
        self.decision_engine.stop()
        self.state_machine.stop()
        self.telemetry.stop()
        self.communication.stop()
        self.backend.stop()
        
        self.logger.info("DroneAgent shutdown complete")
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DroneAgent")
    parser.add_argument("-c", "--config", nargs="+", help="Path to config YAML files")
    args = parser.parse_args()
    
    configs = args.config if args.config else ["config/drone1.yaml"]
    
    # Ensure base.yaml is loaded first
    if not any("base.yaml" in c for c in configs):
        configs.insert(0, "config/base.yaml")
        
    # Ensure a mode is loaded
    if not any("simulation.yaml" in c or "real.yaml" in c for c in configs):
        configs.insert(1, "config/simulation.yaml")
        
    if not any("network_config.yaml" in c for c in configs):
        configs.insert(1, "config/network_config.yaml")
        
    drone = DroneAgent(configs)
    drone.start()
