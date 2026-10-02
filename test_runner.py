import time
import logging
from state_machine import StateMachine, DroneState
from formation import Formation
from packet import DronePacket

class MockBackend:
    def __init__(self):
        self.connected = True
        self.emergency = False
        self.RTL = False
        self.failsafe_triggered = False

    def is_connected(self):
        return self.connected

    def reconnect(self):
        self.connected = True
        return True

    def emergency_stop(self):
        self.emergency = True

    def return_to_launch(self):
        self.RTL = True

    def failsafe(self):
        self.failsafe_triggered = True

class MockTelemetry:
    def __init__(self):
        self.battery = 1.0
        self.gps = (47.3977, 8.5455, 500)
    def get_battery(self): return self.battery
    def get_gps(self): return self.gps
    def get_local_position(self): return (0, 0, 0)
    def get_velocity(self): return (0, 0, 0)
    def get_heading(self): return 0.0

class MockComm:
    def __init__(self):
        self.neighbors = {}
    def get_neighbor_list(self): return list(self.neighbors.keys())

def run_tests():
    logging.basicConfig(level=logging.ERROR)
    logger = logging.getLogger("TestRunner")
    
    config = {
        'drone_id': 1,
        'battery_emergency': 0.10,
        'battery_rtl': 0.20,
        'neighbor_list': [2, 3],
        'mission': {'formation': 'v', 'takeoff_altitude': 10}
    }
    
    print("--- Running Logic Tests ---")
    
    # 1. Formation Test (Stage 16)
    form = Formation(config, logger)
    pos = form.get_formation_position(1, {}, MockTelemetry())
    print(f"Formation Logic Result (Drone 1 in V): {pos}")
    assert pos is not None
    
    # 2. Battery RTL Test (Stage 25)
    sm = StateMachine(config, logger, backend=MockBackend(), telemetry=MockTelemetry(), communication=MockComm())
    sm.state = DroneState.MISSION
    sm.telemetry.battery = 0.15 # Under RTL, over Emergency
    sm.update()
    print(f"Low Battery Transition: {sm.state.name}")
    assert sm.state == DroneState.RTL
    
    # 3. Battery Failsafe Test (Stage 25)
    sm.telemetry.battery = 0.05
    sm.update()
    print(f"Critical Battery Transition: {sm.state.name}")
    assert sm.state == DroneState.FAILSAFE
    
    # 4. GPS Loss Test (Stage 24)
    sm = StateMachine(config, logger, backend=MockBackend(), telemetry=MockTelemetry(), communication=MockComm())
    sm.state = DroneState.MISSION
    sm.telemetry.gps = (0.0, 0.0)
    sm.update()
    print(f"GPS Loss Transition: {sm.state.name}")
    assert sm.state == DroneState.FAILSAFE
    
    # 5. Backend Disconnect Test (Stage 26 & 27)
    sm = StateMachine(config, logger, backend=MockBackend(), telemetry=MockTelemetry(), communication=MockComm())
    sm.state = DroneState.READY
    sm.backend.connected = False
    sm.update() # Should go to EMERGENCY
    print(f"Backend Disconnect Transition: {sm.state.name}")
    assert sm.state == DroneState.EMERGENCY
    
    # Second update should auto-reconnect
    sm.update()
    print(f"Backend Reconnect Transition: {sm.state.name}")
    assert sm.state == DroneState.READY
    assert sm.backend.connected == True
    
    print("--- All Logic Tests Passed ---")

if __name__ == "__main__":
    run_tests()
