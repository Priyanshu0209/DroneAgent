import re

with open('/home/priyanshu/DroneAgent/packet.py', 'r') as f:
    content = f.read()

append_str = """
import json

class CommandPacket:
    \"\"\"
    Command packet sent from GCS to DroneNodes.
    \"\"\"
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
        return b'\\xFF' + json.dumps(data).encode('utf-8')

    @classmethod
    def from_bytes(cls, data: bytes):
        if not data.startswith(b'\\xFF'):
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
"""

if "CommandPacket" not in content:
    with open('/home/priyanshu/DroneAgent/packet.py', 'a') as f:
        f.write(append_str)

