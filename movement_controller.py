#!/usr/bin/env python3
"""
Movement Controller for DroneAgent

Handles sending movement commands to the MAVSDK controller based on
desired state from the decision engine/planner.
"""

import threading
import time
import math
import logging
from typing import Optional, Tuple


class MovementController:
    def __init__(self, config: dict, logger: logging.Logger,
                 backend=None, decision_engine=None,
                 state_machine=None, planner=None, telemetry=None):
        """
        Initialize movement controller.

        Args:
            config: Configuration dictionary
            logger: Logger instance
            backend: HardwareInterface instance
            decision_engine: DecisionEngine instance (for getting desired state)
            state_machine: StateMachine instance (for checking state)
        """
        self.config = config
        self.logger = logger.getChild("MovementController")
        self.backend = backend
        self.decision_engine = decision_engine
        self.state_machine = state_machine
        self.planner = planner
        self.telemetry = telemetry

        self._running = False
        self._thread = None
        self._manual_velocity = (0.0, 0.0, 0.0, 0.0)

        # Control parameters
        self.control_rate = config.get('control_rate', 50)  # Hz

    def set_manual_velocity(self, vx, vy, vz, yaw):
        self._manual_velocity = (vx, vy, vz, yaw)

    def start(self):
        """Start the movement controller loop."""
        self._running = True
        self._thread = threading.Thread(target=self._control_loop, name="MovementControl", daemon=True)
        self._thread.start()
        self.logger.info("Movement controller started")

    def stop(self):
        """Stop the movement controller loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self.logger.info("Movement controller stopped")

    def _control_loop(self):
        """Main loop: get desired state and send to MAVSDK controller."""
        while self._running:
            start_time = time.time()
            try:
                # Only send commands if in OFFBOARD state and armed
                if self.state_machine and self.backend and self.backend.is_armed():
                    state_name = self.state_machine.get_state().name

                    if state_name == "RTL":
                        self._manual_velocity = (0.0, 0.0, 0.0, 0.0)
                        continue

                    elif state_name == "OFFBOARD":
                        vx, vy, vz, yaw = self._manual_velocity
                        if hasattr(self.backend, 'set_velocity_ned'):
                            self.backend.set_velocity_ned(vx, vy, vz, yaw)

                    elif state_name in ["FORMATION", "MISSION"]:
                        if self.decision_engine and self.planner and self.telemetry:
                            # 1. Update Planner State
                            current_pos = self.telemetry.get_local_position()
                            current_vel = self.telemetry.get_velocity()
                            current_yaw = self.telemetry.get_heading()
                            
                            if current_pos and current_vel and current_yaw is not None:
                                self.planner.update_state(current_pos, current_vel, current_yaw)
                                
                                # 2. Set Planner Target from Decision Engine
                                pos_ned, vel_ned, target_yaw = self.decision_engine.get_desired_state()
                                if pos_ned is not None and vel_ned is not None:
                                    self.planner.set_target(pos_ned, vel_ned, target_yaw)
                                    
                                    # 3. Get Smoothed Command
                                    dt = 1.0 / self.control_rate
                                    pos_cmd, vel_cmd, yaw_cmd = self.planner.get_control_command(dt)
                                    
                                    # 4. Send to Backend
                                    yaw_deg = math.degrees(yaw_cmd)
                                    try:
                                        if hasattr(self.backend, 'set_velocity_ned'):
                                            self.backend.set_velocity_ned(vel_cmd[0], vel_cmd[1], vel_cmd[2], yaw_deg)
                                        else:
                                            self.backend.set_position_ned(pos_cmd[0], pos_cmd[1], pos_cmd[2], yaw_deg)
                                    except Exception as e:
                                        self.logger.error(f"Failed to send movement command: {e}")
                        else:
                            # Fallback if no decision engine / planner
                            if self.decision_engine:
                                pos_ned, vel_ned, yaw = self.decision_engine.get_desired_state()
                                if pos_ned is not None and vel_ned is not None:
                                    try:
                                        yaw_deg = math.degrees(yaw)
                                        if hasattr(self.backend, 'set_velocity_ned') and vel_ned != (0.0, 0.0, 0.0):
                                            self.backend.set_velocity_ned(vel_ned[0], vel_ned[1], vel_ned[2], yaw_deg)
                                        else:
                                            self.backend.set_position_ned(pos_ned[0], pos_ned[1], pos_ned[2], yaw_deg)
                                    except Exception as e:
                                        self.logger.error(f"Failed to send position setpoint: {e}")
                
                # Sleep to maintain rate
                elapsed = time.time() - start_time
                sleep_time = max(0, (1.0 / self.control_rate) - elapsed)
                time.sleep(sleep_time)
            except Exception as e:
                self.logger.error(f"Error in control loop: {e}")
                time.sleep(0.1)


if __name__ == "__main__":
    # Simple test (requires actual drone or SITL running)
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("Test")

    config = {
        'control_rate': 50
    }

    controller = MovementController(config, logger)
    controller.start()
    try:
        time.sleep(5)
    finally:
        controller.stop()