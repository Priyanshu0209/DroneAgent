import re

with open('gui/toolbar.py', 'r') as f:
    content = f.read()

# Add logging
if 'import logging' not in content:
    content = "import logging\n" + content

if 'self.logger = ' not in content:
    content = re.sub(r'(def __init__\(self, agent, parent=None\):\n        super\(\)\.__init__\(parent\)\n        self.agent = agent)',
                     r'\1\n        self.logger = logging.getLogger("Toolbar")', content)

handler = """
    def _handle_future(self, cmd_name, future):
        if future is None:
            return
        self.logger.info(f"Command Sent: {cmd_name}")
        def callback(fut):
            try:
                fut.result()
                self.logger.info(f"Command Success: {cmd_name}")
            except Exception as e:
                self.logger.error(f"Command Failed: {cmd_name} - {e}")
        future.add_done_callback(callback)
"""
if '_handle_future' not in content:
    content = content.replace('    def on_connect(self):', handler + '\n    def on_connect(self):')

# Replace on_takeoff, on_disarm, etc.
def wrap_cmd(match):
    name = match.group(1)
    body = match.group(2)
    # The body has something like `self.agent.backend.takeoff(alt)`
    # We want to replace it with `future = self.agent.backend.takeoff(...)` and `self._handle_future("takeoff", future)`
    # Or just capture the line that starts with `self.agent.backend`
    
    # We'll just manually replace the common ones in the file
    pass

# We can just do string replacements for the specific methods since there are only a few.
methods = {
    'on_disarm': 'disarm()',
    'on_land': 'land()',
    'on_rtl': 'return_to_launch()',
    'on_kill': 'emergency_stop()'
}

for meth, cmd in methods.items():
    old = f"    def {meth}(self):\n        if hasattr(self.agent, 'backend') and self.agent.backend:\n            self.agent.backend.{cmd}"
    new = f"""    def {meth}(self):
        self.logger.info(f"Button Clicked: {meth.replace('on_', '').upper()}")
        if hasattr(self.agent, 'backend') and self.agent.backend:
            fut = self.agent.backend.{cmd}
            self._handle_future('{meth.replace('on_', '').upper()}', fut)"""
    content = content.replace(old, new)

# Takeoff is slightly different
old_takeoff = """    def on_takeoff(self):
        if hasattr(self.agent, 'backend') and self.agent.backend:
            alt = self.agent.config.get('mission', {}).get('takeoff_altitude', 10.0)
            self.agent.backend.takeoff(alt)"""
new_takeoff = """    def on_takeoff(self):
        self.logger.info("Button Clicked: TAKEOFF")
        if hasattr(self.agent, 'backend') and self.agent.backend:
            alt = self.agent.config.get('mission', {}).get('takeoff_altitude', 10.0)
            fut = self.agent.backend.takeoff(alt)
            self._handle_future('TAKEOFF', fut)"""
content = content.replace(old_takeoff, new_takeoff)

# Arm
old_arm = """    def on_arm(self):
        if hasattr(self.agent, 'state_machine'):
            self.agent.state_machine.transition('arm_command')"""
new_arm = """    def on_arm(self):
        self.logger.info("Button Clicked: ARM")
        if hasattr(self.agent, 'state_machine'):
            self.agent.state_machine.transition('arm_command')
        elif hasattr(self.agent, 'backend') and self.agent.backend:
            fut = self.agent.backend.arm()
            self._handle_future('ARM', fut)"""
content = content.replace(old_arm, new_arm)

# Emergency
old_emg = """    def on_emergency(self):
        if hasattr(self.agent, 'state_machine'):
            self.agent.state_machine.transition('emergency')"""
new_emg = """    def on_emergency(self):
        self.logger.info("Button Clicked: EMERGENCY")
        if hasattr(self.agent, 'state_machine'):
            self.agent.state_machine.transition('emergency')"""
content = content.replace(old_emg, new_emg)


with open('gui/toolbar.py', 'w') as f:
    f.write(content)
