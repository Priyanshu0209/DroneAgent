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
        self.movement_controller = MovementController(
            self.config, self.logger,
            backend=self.backend,
            decision_engine=self.decision_engine,
            state_machine=self.state_machine
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
        
        # Main thread wait or PySide6 execution
        if self.config.get('run_gui', True):
            from PySide6.QtWidgets import QApplication
            from gui.main_window import MainWindow
            
            # Use instance if available (e.g. running multiple times in same python process)
            app = QApplication.instance()
            if not app:
                app = QApplication(sys.argv)
                
            try:
                import os
                style_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui", "styles.qss")
                with open(style_path, "r") as f:
                    app.setStyleSheet(f.read())
            except FileNotFoundError:
                self.logger.warning("GUI style sheet not found.")
                
            main_window = MainWindow(self)
            main_window.show()
            
            self.logger.info("Starting PySide6 GUI Loop")
            app.exec()
            # The app loop exits when the main window is closed
            if not self.shutdown_event.is_set():
                self.shutdown()
        else:
            try:
                while not self.shutdown_event.is_set():
                    time.sleep(0.1)
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
            finally:
                self.shutdown()
    
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
        
    drone = DroneAgent(configs)
    drone.start()
