#!/usr/bin/env python3
"""
Packet Definitions for DroneAgent Communication

Defines the packet structure used for drone-to-drone communication in the mesh network.
Includes serialization, deserialization, CRC validation, and timestamp validation.
"""

import struct
import time
import zlib
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import math

# Packet structure format (little-endian)
# All fields are in SI units unless otherwise noted
# We'll use a fixed-size binary format for efficiency and determinism
PACKET_FORMAT = (
    "<"  # Little endian
    "I"  # drone_id (uint32)
    "Q"  # timestamp (uint64, microseconds since epoch)
    "fff"  # gps_lat, gps_lon, gps_alt (float)
    "fff"  # local_pos_x, local_pos_y, local_pos_z (float, NED relative to home)
    "fff"  # velocity_x, velocity_y, velocity_z (float, m/s)
    "f"    # heading (float, radians)
    "f"    # altitude (float, meters above ground)
    "f"    # battery (float, 0.0 to 1.0)
    "f"    # health (float, 0.0 to 1.0)
    "I"    # mission_id (uint32)
    "B"    # formation_index (uint8, index into formation pattern)
    "B"    # status_flags (uint8, bitmask: 0=armed, 1=guided, 2=armed, etc.)
    "I"    # packet_number (uint32, per-drone sequence)
    "I"    # checksum (uint32, CRC32 of packet excluding this field)
)
# Calculate expected packet size
PACKET_SIZE = struct.calcsize(PACKET_FORMAT)
# Note: The checksum field is included in the struct, so we calculate over the packet without it

# Actually, let's restructure: we'll compute checksum over all fields except the checksum itself.
# We'll define the format without the checksum field, then append it.

# Format without checksum (for calculation)
PACKET_FORMAT_NO_CHK = PACKET_FORMAT[:-1]  # Remove the last 'I' (checksum)
PACKET_SIZE_NO_CHK = struct.calcsize(PACKET_FORMAT_NO_CHK)

@dataclass
class DronePacket:
    """
    Data structure representing a drone's state and mission.
    """
    drone_id: int
    timestamp: int  # microseconds since epoch
    gps_lat: float
    gps_lon: float
    gps_alt: float
    local_pos_x: float
    local_pos_y: float
    local_pos_z: float
    velocity_x: float
    velocity_y: float
    velocity_z: float
    heading: float  # radians
    altitude: float  # meters above ground
    battery: float  # 0.0 to 1.0
    health: float   # 0.0 to 1.0
    mission_id: int
    formation_index: int  # Index into formation pattern (formation.py)
    status_flags: int   # Bitmask for drone state
    packet_number: int  # Monotonically increasing per drone
    
    def to_bytes(self) -> bytes:
        """
        Serialize the packet to bytes, including CRC checksum.
        
        Returns:
            bytes: The packed packet (including checksum)
        """
        # Pack all fields except checksum
        data = struct.pack(
            PACKET_FORMAT_NO_CHK,
            self.drone_id,
            self.timestamp,
            self.gps_lat,
            self.gps_lon,
            self.gps_alt,
            self.local_pos_x,
            self.local_pos_y,
            self.local_pos_z,
            self.velocity_x,
            self.velocity_y,
            self.velocity_z,
            self.heading,
            self.altitude,
            self.battery,
            self.health,
            self.mission_id,
            self.formation_index,
            self.status_flags,
            self.packet_number
        )
        # Calculate CRC32 checksum
        checksum = zlib.crc32(data) & 0xffffffff
        # Pack checksum and append
        return data + struct.pack("<I", checksum)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> Optional['DronePacket']:
        """
        Deserialize a packet from bytes, validating checksum.
        
        Args:
            data: Raw packet bytes (including checksum)
            
        Returns:
            DronePacket if valid, None if checksum fails
        """
        if len(data) != struct.calcsize(PACKET_FORMAT):
            # Incorrect length
            return None
        
        # Extract data and checksum
        packet_data = data[:PACKET_SIZE_NO_CHK]
        received_checksum = struct.unpack("<I", data[PACKET_SIZE_NO_CHK:])[0]
        
        # Compute checksum of data
        computed_checksum = zlib.crc32(packet_data) & 0xffffffff
        
        if received_checksum != computed_checksum:
            # Checksum mismatch
            return None
        
        # Unpack data
        unpacked = struct.unpack(PACKET_FORMAT_NO_CHK, packet_data)
        return cls(
            drone_id=unpacked[0],
            timestamp=unpacked[1],
            gps_lat=unpacked[2],
            gps_lon=unpacked[3],
            gps_alt=unpacked[4],
            local_pos_x=unpacked[5],
            local_pos_y=unpacked[6],
            local_pos_z=unpacked[7],
            velocity_x=unpacked[8],
            velocity_y=unpacked[9],
            velocity_z=unpacked[10],
            heading=unpacked[11],
            altitude=unpacked[12],
            battery=unpacked[13],
            health=unpacked[14],
            mission_id=unpacked[15],
            formation_index=unpacked[16],
            status_flags=unpacked[17],
            packet_number=unpacked[18]
        )
    
    def is_timestamp_valid(self, max_age_seconds: float = 1.0) -> bool:
        """
        Check if the packet timestamp is recent enough.
        
        Args:
            max_age_seconds: Maximum allowed age in seconds
            
        Returns:
            True if timestamp is within max_age_seconds of now
        """
        now = int(time.time() * 1_000_000)  # microseconds
        age = (now - self.timestamp) / 1_000_000.0
        return age <= max_age_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert packet to dictionary for logging/debugging."""
        return asdict(self)

# Constants for status flags (bitmask)
STATUS_ARMED = 0x01
STATUS_GUIDED_MODE = 0x02
STATUS_ARMED_AND_GUIDED = STATUS_ARMED | STATUS_GUIDED_MODE
STATUS_OFFBOARD = 0x04
STATUS_PRECARM = 0x08
STATUS_GOOD_GPS = 0x10
STATUS_EKF_OK = 0x20

if __name__ == "__main__":
    # Simple test
    pkt = DronePacket(
        drone_id=1,
        timestamp=int(time.time() * 1_000_000),
        gps_lat=47.397742,
        gps_lon=8.545594,
        gps_alt=500.0,
        local_pos_x=0.0,
        local_pos_y=0.0,
        local_pos_z=0.0,
        velocity_x=0.0,
        velocity_y=0.0,
        velocity_z=0.0,
        heading=0.0,
        altitude=50.0,
        battery=0.9,
        health=0.95,
        mission_id=1,
        formation_index=0,
        status_flags=STATUS_ARMED | STATUS_GUIDED_MODE,
        packet_number=0
    )
    
    data = pkt.to_bytes()
    print(f"Packet size: {len(data)} bytes")
    
    pkt2 = DronePacket.from_bytes(data)
    if pkt2:
        print("Packet deserialized successfully:")
        print(pkt2.to_dict())
    else:
        print("Packet checksum failed")

import json

class CommandPacket:
    """
    Command packet sent from GCS to DroneNodes.
    """
    def __init__(self, target_id: int, command: str, args: dict = None):
        self.target_id = target_id
        self.command = command
        self.args = args or {}
        self.timestamp = int(time.time() * 1_000_000)

    def to_bytes(self) -> bytes:
        data = {
            '_type': 'command',
            'target_id': self.target_id,
            'command': self.command,
            'args': self.args,
            'timestamp': self.timestamp
        }
        # Prepend a special magic byte to distinguish from DronePacket
        return b'\xFF' + json.dumps(data).encode('utf-8')

    @classmethod
    def from_bytes(cls, data: bytes):
        if not data.startswith(b'\xFF'):
            return None
        try:
            payload = data[1:].decode('utf-8')
            parsed = json.loads(payload)
            if parsed.get('_type') == 'command':
                pkt = cls(parsed['target_id'], parsed['command'], parsed.get('args', {}))
                pkt.timestamp = parsed.get('timestamp', int(time.time() * 1_000_000))
                return pkt
        except Exception:
            pass
        return None
