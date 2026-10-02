import re

# 1. Update Backends
def add_pause_resume(filename):
    with open(filename, 'r') as f:
        content = f.read()
    
    if 'def pause(self):' not in content:
        pause_code = """
    def pause(self):
        self.logger.info("Pausing vehicle...")
        try:
            return asyncio.run_coroutine_threadsafe(self._pause(), self._loop_instance)
        except Exception as e:
            self.logger.error(f"Pause failed: {e}")
            raise
            
    async def _pause(self):
        from mavsdk.action import ActionError
        try:
            await self._system.action.hold()
        except ActionError as e:
            self.logger.error(f"MAVSDK Pause ActionError: {e}")
            raise
            
    def resume(self):
        self.logger.info("Resuming mission...")
        try:
            return asyncio.run_coroutine_threadsafe(self._resume(), self._loop_instance)
        except Exception as e:
            self.logger.error(f"Resume failed: {e}")
            raise
            
    async def _resume(self):
        from mavsdk.mission import MissionError
        try:
            await self._system.mission.start_mission()
        except MissionError as e:
            self.logger.error(f"MAVSDK Resume MissionError: {e}")
            raise
"""
        content = content.replace("    def set_position_ned", pause_code + "\n    def set_position_ned")
        with open(filename, 'w') as f:
            f.write(content)

add_pause_resume('simulation_backend.py')
add_pause_resume('real_backend.py')

# 2. Update toolbar.py
with open('gui/toolbar.py', 'r') as f:
    tb = f.read()

# Fix arm
arm_old = """    def on_arm(self):
        self.logger.info("Button Clicked: ARM")
        if hasattr(self.agent, 'state_machine'):
            self.agent.state_machine.transition('arm_command')
        elif hasattr(self.agent, 'backend') and self.agent.backend:
            fut = self.agent.backend.arm()
            self._handle_future('ARM', fut)"""
arm_new = """    def on_arm(self):
        self.logger.info("Button Clicked: ARM")
        if hasattr(self.agent, 'backend') and self.agent.backend:
            fut = self.agent.backend.arm()
            self._handle_future('ARM', fut)
        if hasattr(self.agent, 'state_machine'):
            self.agent.state_machine.transition('arm_command')"""
if arm_old in tb:
    tb = tb.replace(arm_old, arm_new)

# Fix pause / resume
pause_old = """    def on_pause(self):
        # Mission pausing could be handled by the mission manager
        pass"""
pause_new = """    def on_pause(self):
        self.logger.info("Button Clicked: PAUSE")
        if hasattr(self.agent, 'backend') and self.agent.backend:
            fut = self.agent.backend.pause()
            self._handle_future('PAUSE', fut)"""
tb = tb.replace(pause_old, pause_new)

resume_old = """    def on_resume(self):
        # Mission resuming
        pass"""
resume_new = """    def on_resume(self):
        self.logger.info("Button Clicked: RESUME")
        if hasattr(self.agent, 'backend') and self.agent.backend:
            fut = self.agent.backend.resume()
            self._handle_future('RESUME', fut)"""
tb = tb.replace(resume_old, resume_new)

with open('gui/toolbar.py', 'w') as f:
    f.write(tb)

# 3. Update formation_panel.py
with open('gui/formation_panel.py', 'r') as f:
    fp = f.read()

apply_old = """        if hasattr(self.agent, 'decision_engine'):
            # The decision engine typically handles formations in this architecture
            # Alternatively, it could be the formation module directly.
            # Assuming agent.formation or agent.decision_engine has a set_formation method.
            pass"""
apply_new = """        
        if not hasattr(self.agent, 'config'):
            self.agent.config = {}
        if 'formation' not in self.agent.config:
            self.agent.config['formation'] = {}
            
        self.agent.config['formation'].update({
            'shape': shape,
            'spacing': spacing,
            'heading': heading,
            'alt_offset': alt_offset,
            'rotation': rotation
        })
        if hasattr(self.agent, 'logger'):
            self.agent.logger.info(f"Formation updated to {shape} with spacing {spacing} from GUI")
"""
fp = fp.replace(apply_old, apply_new)
with open('gui/formation_panel.py', 'w') as f:
    f.write(fp)

# 4. Update parameter_panel.py
with open('gui/parameter_panel.py', 'r') as f:
    pp = f.read()

update_old = """        # Example mapping (assuming agent.config can be updated dynamically)
        # In a real scenario, setter methods on respective modules should be called
        pass"""
update_new = """        if not hasattr(self.agent, 'config'):
            self.agent.config = {}
        for name, spinbox in self.params.items():
            val = spinbox.value()
            if name == "Speed (m/s)":
                self.agent.config['max_speed'] = val
            elif name == "Altitude (m)":
                if 'mission' not in self.agent.config: self.agent.config['mission'] = {}
                self.agent.config['mission']['takeoff_altitude'] = val
            elif name == "Collision Radius (m)":
                self.agent.config['collision_radius'] = val
            elif name == "Heartbeat Freq (Hz)":
                self.agent.config['heartbeat_frequency'] = val
                
        if hasattr(self.agent, 'logger'):
            self.agent.logger.info("Live parameters updated from GUI.")"""
pp = pp.replace(update_old, update_new)
with open('gui/parameter_panel.py', 'w') as f:
    f.write(pp)

# 5. Update swarm_panel.py
with open('gui/swarm_panel.py', 'r') as f:
    sp = f.read()

swarm_old = """        if hasattr(self.agent, 'communication'):
            # self.agent.communication.broadcast_command(cmd)
            pass"""
swarm_new = """        if hasattr(self.agent, 'communication') and self.agent.communication:
            self.agent.communication.broadcast_command(cmd)
            if hasattr(self.agent, 'logger'):
                self.agent.logger.info(f"Broadcasted swarm command: {cmd}")"""
sp = sp.replace(swarm_old, swarm_new)
with open('gui/swarm_panel.py', 'w') as f:
    f.write(sp)

print("GUI Refactor Complete.")
