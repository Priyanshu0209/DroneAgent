#!/usr/bin/env python3
"""
State Machine for DroneAgent

Defines the drone's behavior states and transitions:
BOOT, CONNECTING, DISCOVERING, WAITING_MISSION, READY, ARMING, TAKEOFF,
OFFBOARD, FORMATION, MISSION, RTL, LAND, EMERGENCY, FAILSAFE

Each state has entry/exit actions and transition conditions.
"""

import threading
import time
from enum import Enum, auto
from typing import Optional, Callable, Dict, Any
import logging

class DroneState(Enum):
    BOOT = auto()
    CONNECTING = auto()
    DISCOVERING = auto()
    WAITING_MISSION = auto()
    READY = auto()
    ARMING = auto()
    TAKEOFF = auto()
    OFFBOARD = auto()
    FORMATION = auto()
    MISSION = auto()
    RTL = auto()
    LAND = auto()
    EMERGENCY = auto()
    FAILSAFE = auto()

class StateMachine:
    def __init__(self, config: dict, logger: logging.Logger, backend=None, telemetry=None, communication=None):
        """
        Initialize the state machine.
        
        Args:
            config: Configuration dictionary
            logger: Logger instance
        """
        self.config = config
        self.logger = logger.getChild("StateMachine")
        self.state = DroneState.BOOT
        self._lock = threading.RLock()
        self._transition_callbacks: Dict[tuple, Callable] = {}
        self._state_callbacks: Dict[DroneState, tuple] = {}  # state -> (enter, exit)
        
        # Initialize hardware backend and subsystems for flight control
        self.backend = backend
        self.telemetry = telemetry
        self.communication = communication

        # State-related data that might be updated by other modules
        self._status_flags = 0
        self._mission_id = 0
        self._formation_index = 0
        self._running = False
        
        # Define state transition table: (from_state, trigger) -> to_state
        self._transitions = {
            # Boot sequence
            (DroneState.BOOT, 'system_ready'): DroneState.CONNECTING,
            (DroneState.CONNECTING, 'backend_connected'): DroneState.DISCOVERING,
            (DroneState.DISCOVERING, 'neighbors_found'): DroneState.WAITING_MISSION,
            (DroneState.WAITING_MISSION, 'mission_received'): DroneState.READY,
            
            # Arming and takeoff
            (DroneState.READY, 'arm_command'): DroneState.ARMING,
            (DroneState.ARMING, 'armed'): DroneState.TAKEOFF,
            (DroneState.TAKEOFF, 'takeoff_complete'): DroneState.OFFBOARD,
            
            # Formation and mission
            (DroneState.OFFBOARD, 'formation_ready'): DroneState.FORMATION,
            (DroneState.FORMATION, 'mission_start'): DroneState.MISSION,
            
            # Mission execution
            (DroneState.MISSION, 'mission_complete'): DroneState.RTL,
            (DroneState.MISSION, 'emergency'): DroneState.EMERGENCY,
            
            # Return and landing
            (DroneState.RTL, 'home_reached'): DroneState.LAND,
            (DroneState.LAND, 'landed'): DroneState.READY,
            
            # Emergency handling (can happen from any state)
            (DroneState.BOOT, 'emergency'): DroneState.EMERGENCY,
            (DroneState.CONNECTING, 'emergency'): DroneState.EMERGENCY,
            (DroneState.DISCOVERING, 'emergency'): DroneState.EMERGENCY,
            (DroneState.WAITING_MISSION, 'emergency'): DroneState.EMERGENCY,
            (DroneState.READY, 'emergency'): DroneState.EMERGENCY,
            (DroneState.ARMING, 'emergency'): DroneState.EMERGENCY,
            (DroneState.TAKEOFF, 'emergency'): DroneState.EMERGENCY,
            (DroneState.OFFBOARD, 'emergency'): DroneState.EMERGENCY,
            (DroneState.FORMATION, 'emergency'): DroneState.EMERGENCY,
            (DroneState.MISSION, 'emergency'): DroneState.EMERGENCY,
            (DroneState.RTL, 'emergency'): DroneState.EMERGENCY,
            (DroneState.LAND, 'emergency'): DroneState.EMERGENCY,
            
            # Failsafe (e.g., low battery, loss of GPS) - similar to emergency but may allow recovery
            (DroneState.BOOT, 'failsafe'): DroneState.FAILSAFE,
            (DroneState.CONNECTING, 'failsafe'): DroneState.FAILSAFE,
            (DroneState.DISCOVERING, 'failsafe'): DroneState.FAILSAFE,
            (DroneState.WAITING_MISSION, 'failsafe'): DroneState.FAILSAFE,
            (DroneState.READY, 'failsafe'): DroneState.FAILSAFE,
            (DroneState.ARMING, 'failsafe'): DroneState.FAILSAFE,
            (DroneState.TAKEOFF, 'failsafe'): DroneState.FAILSAFE,
            (DroneState.OFFBOARD, 'failsafe'): DroneState.FAILSAFE,
            (DroneState.FORMATION, 'failsafe'): DroneState.FAILSAFE,
            (DroneState.MISSION, 'failsafe'): DroneState.FAILSAFE,
            (DroneState.RTL, 'failsafe'): DroneState.FAILSAFE,
            (DroneState.LAND, 'failsafe'): DroneState.FAILSAFE,
            
            # Recovery from failsafe/emergency
            (DroneState.EMERGENCY, 'recover'): DroneState.READY,
            (DroneState.FAILSAFE, 'recover'): DroneState.READY,
        }
        
        # Set up default state callbacks
        self._setup_state_callbacks()
        
        self.logger.info("StateMachine initialized")
    
    def _setup_state_callbacks(self):
        """Define entry and exit actions for each state."""
        self._state_callbacks = {
            DroneState.BOOT: (self._enter_boot, self._exit_boot),
            DroneState.CONNECTING: (self._enter_connecting, self._exit_connecting),
            DroneState.DISCOVERING: (self._enter_discovering, self._exit_discovering),
            DroneState.WAITING_MISSION: (self._enter_waiting_mission, self._exit_waiting_mission),
            DroneState.READY: (self._enter_ready, self._exit_ready),
            DroneState.ARMING: (self._enter_arming, self._exit_arming),
            DroneState.TAKEOFF: (self._enter_takeoff, self._exit_takeoff),
            DroneState.OFFBOARD: (self._enter_offboard, self._exit_offboard),
            DroneState.FORMATION: (self._enter_formation, self._exit_formation),
            DroneState.MISSION: (self._enter_mission, self._exit_mission),
            DroneState.RTL: (self._enter_rtl, self._exit_rtl),
            DroneState.LAND: (self._enter_land, self._exit_land),
            DroneState.EMERGENCY: (self._enter_emergency, self._exit_emergency),
            DroneState.FAILSAFE: (self._enter_failsafe, self._exit_failsafe),
        }
    
    def transition(self, trigger: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Trigger a state transition.
        
        Args:
            trigger: The trigger name (e.g., 'arm_command')
            context: Optional context data for the transition
            
        Returns:
            True if transition occurred, False if no transition defined
        """
        with self._lock:
            current_state = self.state
            key = (current_state, trigger)
            if key in self._transitions:
                next_state = self._transitions[key]
                self.logger.info(f"Transition: {current_state.name} --[{trigger}]--> {next_state.name}")
                
                # Exit current state
                exit_action = self._state_callbacks[current_state][1]
                if exit_action:
                    exit_action()
                
                # Enter new state
                self.state = next_state
                enter_action = self._state_callbacks[next_state][0]
                if enter_action:
                    try:
                        enter_action(context)
                    except TypeError:
                        enter_action()
                
                return True
            else:
                self.logger.debug(f"No transition defined for {current_state.name} --[{trigger}]--> ?")
                return False
    
    def get_state(self) -> DroneState:
        """Get current state."""
        return self.state
    
    def get_status_flags(self) -> int:
        return self._status_flags
        
    def set_status_flags(self, flags: int):
        self._status_flags = flags

    def get_mission_id(self) -> int:
        return self._mission_id

    def set_mission_id(self, mission_id: int):
        self._mission_id = mission_id
        
    def get_formation_index(self) -> int:
        return self._formation_index
        
    def set_formation_index(self, index: int):
        self._formation_index = index
    
    # State entry/exit actions
    def _enter_boot(self):
        self.logger.info("Booting up...")
        # Initialize hardware, load config, etc.
    
    def _exit_boot(self):
        pass
    
    def _enter_connecting(self):
        self.logger.info("Connecting to Hardware Backend...")
        # Start Backend connection
        if self.backend:
            self.backend.connect()
    
    def _exit_connecting(self):
        pass
    
    def _enter_discovering(self):
        self.logger.info("Discovering neighbors...")
        # Start neighbor discovery (handled by communication module)
    
    def _exit_discovering(self):
        pass
    
    def _enter_waiting_mission(self):
        self.logger.info("Waiting for mission upload from DSOS...")
    
    def _exit_waiting_mission(self):
        pass
    
    def _enter_ready(self):
        self.logger.info("Ready to arm")
    
    def _exit_ready(self):
        pass
    
    def _enter_arming(self):
        self.logger.info("Arming motors...")
        if self.backend:
            self.backend.arm()
    
    def _exit_arming(self):
        pass
    
    def _enter_takeoff(self):
        self.logger.info(f"Taking off to {self.config['mission']['takeoff_altitude']}m...")
        if self.backend:
            self.backend.takeoff(self.config['mission']['takeoff_altitude'])
    
    def _exit_takeoff(self):
        pass
    
    def _enter_offboard(self):
        self.logger.info("Switching to offboard mode...")
        if self.backend:
            self.backend.set_offboard_mode()
    
    def _exit_offboard(self):
        pass
    
    def _enter_formation(self):
        formation_type = self.config['mission']['formation']
        self.logger.info(f"Forming {formation_type} formation...")
        # Formation logic will be handled by formation module
    
    def _exit_formation(self):
        pass
    
    def _enter_mission(self):
        self.logger.info("Starting mission...")
        # Mission execution handled by mission module
    
    def _exit_mission(self):
        pass
    
    def _enter_rtl(self):
        self.logger.info("Returning to launch...")
        if self.backend:
            self.backend.return_to_launch()
    
    def _exit_rtl(self):
        pass
    
    def _enter_land(self):
        self.logger.info("Landing...")
        if self.backend:
            self.backend.land()
    
    def _exit_land(self):
        pass
    
    def _enter_emergency(self):
        self.logger.warning("EMERGENCY: Emergency stop initiated!")
        if self.backend:
            self.backend.emergency_stop()
    
    def _exit_emergency(self):
        pass
    
    def _enter_failsafe(self):
        self.logger.warning("FAILSAFE: Initiating failsafe procedure...")
        if self.backend:
            self.backend.failsafe()
    
    def _exit_failsafe(self):
        pass
    
    def update_loop(self):
        """Loop to check conditions for automatic transitions."""
        self._running = True
        while getattr(self, '_running', True):
            try:
                self.update()
                time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Error in state machine update loop: {e}")
                time.sleep(0.5)

    def stop(self):
        self._running = False

    def update(self):
        """
        Called periodically to check for state-based transitions and safety rules.
        """
        with self._lock:
            current_state = self.state

        if current_state in [DroneState.BOOT, DroneState.CONNECTING]:
            return

        # Backend Health Check
        if self.backend and not self.backend.is_connected():
            if current_state not in [DroneState.EMERGENCY]:
                self.logger.error("Backend connection lost! Triggering EMERGENCY.")
                self.transition('emergency')
            else:
                self.logger.info("Attempting to reconnect backend...")
                if self.backend.reconnect():
                    self.logger.info("Backend reconnected successfully! Recovering from EMERGENCY...")
                    self.transition('recover')
            return

        # Telemetry Safety Checks
        if self.telemetry:
            # Battery Failsafe
            batt = self.telemetry.get_battery()
            if batt is not None and batt < self.config.get('battery_emergency', 0.10):
                if current_state not in [DroneState.LAND, DroneState.EMERGENCY, DroneState.FAILSAFE]:
                    self.logger.warning("CRITICAL BATTERY! Triggering FAILSAFE (Land).")
                    self.transition('failsafe')
                    return
            elif batt is not None and batt < self.config.get('battery_rtl', 0.20):
                if current_state in [DroneState.MISSION, DroneState.FORMATION, DroneState.OFFBOARD]:
                    self.logger.warning("Low battery! Triggering RTL.")
                    self.transition('mission_complete') # Transition to RTL

            # GPS Failsafe
            gps = self.telemetry.get_gps()
            if gps is None or (gps[0] == 0.0 and gps[1] == 0.0):
                if current_state in [DroneState.MISSION, DroneState.FORMATION, DroneState.OFFBOARD]:
                    self.logger.warning("GPS Signal Lost! Triggering FAILSAFE.")
                    self.transition('failsafe')
                    return

        # Neighbor Safety Checks (Communication timeout)
        if self.communication and current_state == DroneState.FORMATION:
            active_neighbors = self.communication.get_neighbor_list()
            # If we lost all neighbors during a formation, transition to a safe state
            if len(active_neighbors) == 0 and len(self.config.get('neighbor_list', [])) > 0:
                self.logger.warning("All neighbors lost! Recalculating or continuing mission autonomously.")
                # We can either stay in FORMATION and it becomes a 1-drone formation (handled by formation.py)
                # Or transition to mission. Handled by decision engine natively!

if __name__ == "__main__":
    # Simple test
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("Test")
    
    config = {
        'drone_id': 1,
        'mission': {
            'takeoff_altitude': 10.0,
            'formation': 'V',
            'mission_id': 1
        }
    }
    
    sm = StateMachine(config, logger)
    sm.transition('system_ready')
    sm.transition('backend_connected')
    sm.transition('neighbors_found')
    sm.transition('mission_received')
    print(f"Current state: {sm.get_state()}")
    sm.transition('arm_command')
    print(f"Current state: {sm.get_state()}")
