import re

# 1. Update map_panel.py
with open('gui/map_panel.py', 'r') as f:
    mp = f.read()

# Replace hardcoded -122.0 and 37.0 with dynamic home coordinates
map_old = """            lat = state.get('latitude', 0.0)
            lon = state.get('longitude', 0.0)
            my_x = (lon - -122.0) * 111000 * math.cos(math.radians(lat))
            my_y = (lat - 37.0) * 111000"""
map_new = """            lat = state.get('latitude', 0.0)
            lon = state.get('longitude', 0.0)
            
            home_lat, home_lon = 37.0, -122.0
            if hasattr(self.agent, 'telemetry'):
                home = self.agent.telemetry.get_home()
                if home:
                    home_lat, home_lon = home[0], home[1]
                else:
                    # If home not set, use first known position
                    if not hasattr(self, '_initial_lat'):
                        self._initial_lat = lat
                        self._initial_lon = lon
                    if hasattr(self, '_initial_lat') and self._initial_lat != 0.0:
                        home_lat = self._initial_lat
                        home_lon = self._initial_lon

            my_x = (lon - home_lon) * 111000 * math.cos(math.radians(home_lat))
            my_y = (lat - home_lat) * 111000"""
mp = mp.replace(map_old, map_new)

map_old_n = """                    nx = (packet.gps_lon - -122.0) * 111000 * math.cos(math.radians(packet.gps_lat))
                    ny = (packet.gps_lat - 37.0) * 111000"""
map_new_n = """                    nx = (packet.gps_lon - home_lon) * 111000 * math.cos(math.radians(home_lat))
                    ny = (packet.gps_lat - home_lat) * 111000"""
mp = mp.replace(map_old_n, map_new_n)

with open('gui/map_panel.py', 'w') as f:
    f.write(mp)


# 2. Update backends
def fix_backend(filename):
    with open(filename, 'r') as f:
        content = f.read()
    
    # Remove early return if offboard not active
    pos_old = """    def set_position_ned(self, north: float, east: float, down: float, yaw_deg: float = 0.0):
        if not self._offboard_active:
            self.logger.warning("Offboard not active, ignoring position setpoint")
            return
        self._position_setpoint = (north, east, down, yaw_deg)"""
    pos_new = """    def set_position_ned(self, north: float, east: float, down: float, yaw_deg: float = 0.0):
        # Buffer setpoint even if offboard not fully active yet
        if not self._offboard_active:
            self.logger.debug("Offboard not fully active, buffering position setpoint")
        self._position_setpoint = (north, east, down, yaw_deg)"""
    content = content.replace(pos_old, pos_new)
    
    vel_old = """    def set_velocity_ned(self, north_m_s: float, east_m_s: float, down_m_s: float, yaw_deg: float = 0.0):
        if not self._offboard_active:
            self.logger.warning("Offboard not active, ignoring velocity setpoint")
            return
        self._velocity_setpoint = (north_m_s, east_m_s, down_m_s, yaw_deg)"""
    vel_new = """    def set_velocity_ned(self, north_m_s: float, east_m_s: float, down_m_s: float, yaw_deg: float = 0.0):
        if not self._offboard_active:
            self.logger.debug("Offboard not fully active, buffering velocity setpoint")
        self._velocity_setpoint = (north_m_s, east_m_s, down_m_s, yaw_deg)"""
    content = content.replace(vel_old, vel_new)
    
    with open(filename, 'w') as f:
        f.write(content)

fix_backend('simulation_backend.py')
fix_backend('real_backend.py')


# 3. Update movement_controller.py
with open('movement_controller.py', 'r') as f:
    mc = f.read()

mc_old = """                if (self.state_machine and
                    self.state_machine.get_state().name == "OFFBOARD" and
                    self.backend and self.backend.is_armed()):"""
mc_new = """                if (self.state_machine and
                    self.state_machine.get_state().name in ["OFFBOARD", "FORMATION", "MISSION"] and
                    self.backend and self.backend.is_armed()):"""
mc = mc.replace(mc_old, mc_new)

# Also ensure it uses velocity setpoint from decision engine
vel_old = """                            try:
                                self.backend.set_position_ned(
                                    pos_ned[0], pos_ned[1], pos_ned[2], yaw_deg
                                )"""
vel_new = """                            try:
                                # Decision engine outputs both pos and vel.
                                # A real controller might mix them, but here we can send velocity for smoother swarm flight.
                                # Wait, if decision engine output velocity, we should use it!
                                if hasattr(self.backend, 'set_velocity_ned') and vel_ned != (0.0, 0.0, 0.0):
                                    self.backend.set_velocity_ned(vel_ned[0], vel_ned[1], vel_ned[2], yaw_deg)
                                else:
                                    self.backend.set_position_ned(pos_ned[0], pos_ned[1], pos_ned[2], yaw_deg)"""
mc = mc.replace(vel_old, vel_new)

with open('movement_controller.py', 'w') as f:
    f.write(mc)

print("Integration Fixes Applied!")
