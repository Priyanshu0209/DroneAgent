#!/usr/bin/env python3
"""
Neighbor Management Module for DroneAgent

Handles discovery, tracking, and removal of neighboring drones in the mesh network.
"""

import time
import logging
import threading
from typing import Dict, Optional, Tuple
from packet import DronePacket

class Neighbor:
    def __init__(self, config: dict, logger: logging.Logger):
        """
        Initialize neighbor management.
        
        Args:
            config: Configuration dictionary
            logger: Logger instance
        """
        self.config = config
        self.logger = logger.getChild("Neighbor")
        self.drone_id = config['drone_id']
        self.communication_timeout = config.get('communication_timeout', 1.0)  # seconds
        self.heartbeat_rate = config.get('heartbeat_rate', 10.0)  # Hz
        
        # Neighbor table: drone_id -> {
        #   'last_packet': DronePacket,
        #   'last_heard': timestamp,
        #   'rssi': Optional[float],  # Received signal strength (if available)
        #   'is_active': bool
        # }
        self.neighbors: Dict[int, dict] = {}
        
        # Initialize with known neighbors from config (optional)
        known_neighbors = config.get('neighbor_list', [])
        for nid in known_neighbors:
            self.neighbors[nid] = {
                'last_packet': None,
                'last_heard': 0,
                'rssi': None,
                'is_active': False
            }
        
        self._lock = threading.RLock()
        self._running = False
        self._cleanup_thread = None
    
    def start(self):
        """Start neighbor management (cleanup thread)."""
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, name="NeighborCleanup", daemon=True)
        self._cleanup_thread.start()
        self.logger.info("Neighbor management started")
    
    def stop(self):
        """Stop neighbor management."""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=2.0)
        self.logger.info("Neighbor management stopped")
    
    def update_neighbor(self, packet: DronePacket, rssi: Optional[float] = None):
        """
        Update or add a neighbor based on a received packet.
        
        Args:
            packet: Received DronePacket
            rssi: Received signal strength indicator (optional)
        """
        drone_id = packet.drone_id
        now = time.time()
        
        if drone_id not in self.neighbors:
            # New neighbor discovered
            with self._lock:
                self.neighbors[drone_id] = {
                    'last_packet': packet,
                    'last_heard': now,
                    'rssi': rssi,
                    'is_active': True
                }
            self.logger.info(f"Discovered new neighbor: drone {drone_id}")
        else:
            # Update existing neighbor
            with self._lock:
                self.neighbors[drone_id]['last_packet'] = packet
                self.neighbors[drone_id]['last_heard'] = now
                if rssi is not None:
                    self.neighbors[drone_id]['rssi'] = rssi
                self.neighbors[drone_id]['is_active'] = True
        
        # Log at debug level to avoid spam
        self.logger.debug(f"Updated neighbor {drone_id}")
    
    def get_neighbor_packet(self, drone_id: int) -> Optional[DronePacket]:
        """
        Get the most recent packet from a neighbor.
        
        Args:
            drone_id: ID of the neighbor drone
            
        Returns:
            DronePacket if the neighbor is active and packet is not stale, else None
        """
        with self._lock:
            neighbor = self.neighbors.get(drone_id)
            if not neighbor:
                return None
            
            # Check if packet is too old
            if time.time() - neighbor['last_heard'] > self.communication_timeout:
                # Neighbor timed out
                if neighbor['is_active']:
                    self.logger.info(f"Neighbor {drone_id} timed out")
                    neighbor['is_active'] = False
                return None
            
            return neighbor['last_packet']
    
    def get_active_neighbors(self) -> Dict[int, DronePacket]:
        """
        Get all currently active neighbors.
        
        Returns:
            Dict mapping drone_id to DronePacket for active neighbors
        """
        active = {}
        now = time.time()
        with self._lock:
            for drone_id, info in self.neighbors.items():
                if info['is_active'] and (now - info['last_heard']) <= self.communication_timeout:
                    active[drone_id] = info['last_packet']
        return active
    
    def get_neighbor_list(self) -> list:
        """Get list of active neighbor IDs."""
        return list(self.get_active_neighbors().keys())
    
    def get_neighbor_count(self) -> int:
        """Get number of active neighbors."""
        return len(self.get_active_neighbors())
    
    def is_neighbor_active(self, drone_id: int) -> bool:
        """Check if a specific neighbor is active."""
        return drone_id in self.get_active_neighbors()
    
    def _cleanup_loop(self):
        """Periodically check for and remove timed out neighbors."""
        while self._running:
            try:
                now = time.time()
                timed_out = []
                with self._lock:
                    for drone_id, info in self.neighbors.items():
                        if info['is_active'] and (now - info['last_heard']) > self.communication_timeout:
                            timed_out.append(drone_id)
                
                for drone_id in timed_out:
                    self.logger.info(f"Removing timed out neighbor: {drone_id}")
                    with self._lock:
                        if drone_id in self.neighbors:
                            self.neighbors[drone_id]['is_active'] = False
                            # Optionally keep the neighbor for a while for historical data
                            # We'll remove it completely after a longer timeout
                            if now - self.neighbors[drone_id]['last_heard'] > self.communication_timeout * 2:
                                del self.neighbors[drone_id]
                
                time.sleep(1.0)  # Check every second
            except Exception as e:
                self.logger.error(f"Error in neighbor cleanup: {e}")
                time.sleep(1.0)

# For backward compatibility, we'll also provide a simple function to check if a packet is recent
def is_packet_recent(packet: DronePacket, max_age: float = 1.0) -> bool:
    """Check if a packet is recent enough."""
    if packet is None:
        return False
    age = (time.time() * 1_000_000 - packet.timestamp) / 1_000_000.0
    return age <= max_age

if __name__ == "__main__":
    # Simple test
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("Test")
    
    config = {
        'drone_id': 1,
        'communication_timeout': 1.0,
        'neighbor_list': [2, 3]
    }
    
    neighbor_manager = Neighbor(config, logger)
    neighbor_manager.start()
    
    # Simulate receiving a packet
    from packet import DronePacket
    
    pkt = DronePacket(
        drone_id=2,
        timestamp=int(time.time() * 1_000_000),
        gps_lat=47.397742, gps_lon=8.545594, gps_alt=500.0,
        local_pos_x=10.0, local_pos_y=0.0, local_pos_z=-50.0,
        velocity_x=0.0, velocity_y=0.0, velocity_z=0.0,
        heading=0.0, altitude=50.0, battery=0.9, health=0.95,
        mission_id=1, formation_index=0, status_flags=0,
        packet_number=1
    )
    
    neighbor_manager.update_neighbor(pkt)
    active = neighbor_manager.get_active_neighbors()
    print(f"Active neighbors: {list(active.keys())}")
    
    neighbor_manager.stop()
