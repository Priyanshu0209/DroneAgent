from abc import ABC, abstractmethod
from typing import Optional, Tuple
import logging

class HardwareInterface(ABC):
    """
    Abstract Base Class for Drone Hardware.
    All backends (Simulation, Real) must implement these methods.
    """
    
    @abstractmethod
    def connect(self) -> bool:
        """Start and connect the backend controller. Returns True if successful."""
        pass
        
    @abstractmethod
    def reconnect(self) -> bool:
        """Reconnect the backend in case of failure. Returns True if successful."""
        pass
        
    @abstractmethod
    def stop(self):
        """Stop the backend controller."""
        pass
        
    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if connected to the drone."""
        pass
        
    @abstractmethod
    def arm(self):
        """Arm the drone."""
        pass
        
    @abstractmethod
    def disarm(self):
        """Disarm the drone."""
        pass
        
    @abstractmethod
    def takeoff(self, altitude: float):
        """Takeoff to specified altitude (meters)."""
        pass
        
    @abstractmethod
    def land(self):
        """Land the drone."""
        pass
        
    @abstractmethod
    def return_to_launch(self):
        """Command drone to return to launch point."""
        pass
        
    @abstractmethod
    def set_offboard_mode(self):
        """Switch to offboard mode."""
        pass
        
    @abstractmethod
    def offboard_stop(self):
        """Stop offboard mode."""
        pass
        
    @abstractmethod
    def emergency_stop(self):
        """Emergency stop (kill motors)."""
        pass
        
    @abstractmethod
    def failsafe(self):
        """Initiates failsafe (return to launch and land)."""
        pass
        
    @abstractmethod
    def set_position_ned(self, north: float, east: float, down: float, yaw_deg: float = 0.0):
        """Set position target in NED coordinates (relative to home)."""
        pass
        
    @abstractmethod
    def set_velocity_ned(self, north_m_s: float, east_m_s: float, down_m_s: float, yaw_deg: float = 0.0):
        """Set velocity target in NED coordinates."""
        pass
        
    # Telemetry and State getters
    @abstractmethod
    def is_armed(self) -> bool:
        """Check if drone is armed."""
        pass
        
    @abstractmethod
    def is_in_air(self) -> bool:
        """Check if drone is in air."""
        pass
        
    @abstractmethod
    def is_offboard_active(self) -> bool:
        """Check if offboard mode is active."""
        pass
        
    # Exposing the drone object directly for complex telemetry streams 
    # (since the original code relies on mavsdk async iterators like `drone.telemetry.home()`)
    @property
    @abstractmethod
    def drone(self):
        """Return the underlying drone instance (e.g., mavsdk.System)."""
        pass
        
    @property
    @abstractmethod
    def loop(self):
        """Return the asyncio event loop used by the backend."""
        pass
