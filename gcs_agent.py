import sys
import time
import signal
import threading
from concurrent.futures import Future
import logging
from typing import Dict, Any

from config import load_config, ConfigurationError
from communication import Communication
from logger import DroneLogger

class GCSFuture(Future):
    """A mock future for GUI callbacks to succeed."""
    def __init__(self, result=True):
        super().__init__()
        self.set_result(result)

class GCSBackend:
    def __init__(self, comm: Communication):
        self.comm = comm
        
    def connect(self):
        pass
        
    def stop(self):
        pass
        
    def arm(self):
        self.comm.broadcast_command('arm')
        return GCSFuture()
        
    def disarm(self):
        self.comm.broadcast_command('disarm')
        return GCSFuture()
        
    def takeoff(self, alt):
        self.comm.broadcast_command('takeoff', {'alt': alt})
        return GCSFuture()
        
    def land(self):
        self.comm.broadcast_command('land')
        return GCSFuture()
        
    def return_to_launch(self):
        self.comm.broadcast_command('rtl')
        return GCSFuture()
        
    def pause(self):
        self.comm.broadcast_command('pause')
        return GCSFuture()
        
    def resume(self):
        self.comm.broadcast_command('resume')
        return GCSFuture()
        
    def emergency_stop(self):
        self.comm.broadcast_command('kill')
        return GCSFuture()

    def set_velocity_ned(self, vx, vy, vz, yaw):
        self.comm.broadcast_command('move', {'vx': vx, 'vy': vy, 'vz': vz, 'yaw': yaw})
        return GCSFuture()
        
    def set_offboard_mode(self):
        self.comm.broadcast_command('set_offboard_mode')
        return GCSFuture()
        
    def offboard_stop(self):
        self.comm.broadcast_command('offboard_stop')
        return GCSFuture()

class GCSMissionManager:
    def __init__(self, comm: Communication):
        self.comm = comm
        
    def upload_mission(self, wps):
        self.comm.broadcast_command('upload_mission', {'waypoints': wps})
        
    def cancel_mission(self):
        self.comm.broadcast_command('cancel_mission')

class GCSStateMachine:
    def __init__(self, comm: Communication):
        self.comm = comm
        
    def transition(self, state):
        self.comm.broadcast_command('transition', {'state': state})

class GCSAgent:
    def __init__(self, config_paths: list):
        self.config = self._load_config(config_paths)
        self.config['drone_id'] = 0  # GCS acts as ID 0
        self.logger = DroneLogger(self.config['drone_id']).get_logger()
        
        # Core communication
        self.communication = Communication(self.config, self.logger)
        
        # Mocks to satisfy GUI
        self.backend = GCSBackend(self.communication)
        self.mission_manager = GCSMissionManager(self.communication)
        self.state_machine = GCSStateMachine(self.communication)
        
        self.shutdown_event = threading.Event()
        
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def _load_config(self, config_paths: list) -> Dict[str, Any]:
        try:
            return load_config(config_paths, validate=False)
        except Exception as e:
            print(f"Failed to load config: {e}")
            sys.exit(1)
            
    def start(self):
        self.logger.info("Starting GCSAgent...")
        self.communication.start()
        threading.Thread(target=self.communication.transmit_loop, daemon=True, name="CommTx").start()
        threading.Thread(target=self.communication.receive_loop, daemon=True, name="CommRx").start()
        
        # Start GUI
        if self.config.get('run_gui', True):
            from PySide6.QtWidgets import QApplication
            from gui.main_window import MainWindow
            
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
            if not self.shutdown_event.is_set():
                self.shutdown()
        else:
            try:
                while not self.shutdown_event.is_set():
                    time.sleep(0.1)
            except KeyboardInterrupt:
                pass
            finally:
                self.shutdown()
                
    def signal_handler(self, signum, frame):
        self.shutdown()
        
    def shutdown(self):
        self.shutdown_event.set()
        self.communication.stop()
        self.logger.info("GCSAgent shutdown complete")
        sys.exit(0)
