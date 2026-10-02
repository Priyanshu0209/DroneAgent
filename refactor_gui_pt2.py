import re

# 1. Update movement_panel.py
with open('gui/movement_panel.py', 'r') as f:
    mp = f.read()

move_old = """    def move(self, direction):
        if hasattr(self.agent, 'movement_controller'):
            # This calls the movement controller API. Actual implementation depends on backend.
            pass
            
    def adjust_param(self, param, delta):
        if hasattr(self.agent, 'movement_controller'):
            pass"""
move_new = """    def move(self, direction):
        if not hasattr(self.agent, 'backend') or not self.agent.backend:
            return
            
        speed = self.agent.config.get('max_speed', 5.0) if self.agent.config else 5.0
        vx, vy, vz, yaw = 0.0, 0.0, 0.0, 0.0
        
        if direction == "forward": vx = speed
        elif direction == "backward": vx = -speed
        elif direction == "right": vy = speed
        elif direction == "left": vy = -speed
        elif direction == "up": vz = -speed
        elif direction == "down": vz = speed
        elif direction == "rotate_left": yaw = -45.0
        elif direction == "rotate_right": yaw = 45.0
        
        try:
            # Safely set offboard mode if not already
            if not getattr(self.agent.backend, '_offboard_active', False):
                self.agent.backend.set_offboard_mode()
            self.agent.backend.set_velocity_ned(vx, vy, vz, yaw)
            if hasattr(self.agent, 'logger'):
                self.agent.logger.info(f"Movement command sent: {direction} ({vx},{vy},{vz}, yaw={yaw})")
        except Exception as e:
            if hasattr(self.agent, 'logger'):
                self.agent.logger.error(f"Failed to move: {e}")
            
    def adjust_param(self, param, delta):
        if not hasattr(self.agent, 'config'): self.agent.config = {}
        if param == "speed":
            self.agent.config['max_speed'] = self.agent.config.get('max_speed', 5.0) + delta
        elif param == "altitude":
            if 'mission' not in self.agent.config: self.agent.config['mission'] = {}
            self.agent.config['mission']['takeoff_altitude'] = self.agent.config['mission'].get('takeoff_altitude', 10.0) + delta
            
        if hasattr(self.agent, 'logger'):
            self.agent.logger.info(f"Adjusted GUI parameter {param} by {delta}")"""
mp = mp.replace(move_old, move_new)
with open('gui/movement_panel.py', 'w') as f:
    f.write(mp)

# 2. Update mission_panel.py
with open('gui/mission_panel.py', 'r') as f:
    misp = f.read()

mis_old = """    def upload_mission(self):
        if hasattr(self.agent, 'mission_manager'):
            # Build waypoints list from table
            pass
            
    def cancel_mission(self):
        if hasattr(self.agent, 'mission_manager'):
            pass"""
mis_new = """    def upload_mission(self):
        wps = []
        for row in range(self.table_waypoints.rowCount()):
            try:
                lat = float(self.table_waypoints.item(row, 0).text())
                lon = float(self.table_waypoints.item(row, 1).text())
                alt = float(self.table_waypoints.item(row, 2).text())
                speed = float(self.table_waypoints.item(row, 3).text())
                wps.append({'lat': lat, 'lon': lon, 'alt': alt, 'speed': speed})
            except Exception:
                pass
                
        if hasattr(self.agent, 'mission_manager'):
            self.agent.mission_manager.upload_mission(wps)
            
        if hasattr(self.agent, 'logger'):
            self.agent.logger.info(f"Mission uploaded with {len(wps)} waypoints")
            
    def cancel_mission(self):
        if hasattr(self.agent, 'mission_manager'):
            self.agent.mission_manager.cancel_mission()
            
        if hasattr(self.agent, 'logger'):
            self.agent.logger.info("Mission cancelled from GUI")"""
misp = misp.replace(mis_old, mis_new)
with open('gui/mission_panel.py', 'w') as f:
    f.write(misp)

print("GUI Part 2 Refactor Complete.")
