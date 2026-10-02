import re

def refactor_file(filename):
    with open(filename, 'r') as f:
        content = f.read()

    # Add ActionError import if not there
    if 'from mavsdk.action import ActionError' not in content:
        content = re.sub(r'from mavsdk import offboard', 'from mavsdk import offboard\nfrom mavsdk.action import ActionError', content)

    # 1. Remove .result(timeout=...) and return the future
    # Example: asyncio.run_coroutine_threadsafe(self._arm(), self._loop_instance).result(timeout=10.0)
    # Becomes: return asyncio.run_coroutine_threadsafe(self._arm(), self._loop_instance)
    content = re.sub(r'(asyncio\.run_coroutine_threadsafe\([^)]+\),\s*self\._loop_instance\))\.result\(timeout=[0-9.]+\)', r'return \1', content)

    # 2. Add safety checks to _takeoff
    takeoff_checks = """
        if not self.is_connected():
            raise Exception("Cannot takeoff: Backend not connected.")
        
        # Check if already armed, otherwise arm
        if not self._armed:
            self.logger.info("Auto-arming before takeoff...")
            try:
                await self._system.action.arm()
                self._armed = True
            except ActionError as e:
                self.logger.error(f"Auto-arm failed: {e}")
                raise Exception("Takeoff aborted: Could not arm.")
"""
    
    # Replace the beginning of _takeoff
    content = re.sub(r'(async def _takeoff\(self, altitude: float\):)', r'\1\n        from mavsdk.action import ActionError' + takeoff_checks, content)

    # 3. Add try/except ActionError to all _* async methods
    # This is slightly tricky with regex, we can just wrap the awaits in try/except manually or use a simpler approach.
    # Actually, if we just want to catch ActionError and log it, we can redefine the async methods to have try/except blocks.
    
    methods = ['_arm', '_disarm', '_land', '_return_to_launch', '_emergency_stop']
    for m in methods:
        pattern = r'(async def ' + m + r'\(self\):\n(?:.|\n)*?)(?=\n    def|\n    async def)'
        def replacer(match):
            block = match.group(1)
            # Find the body (everything after async def line)
            lines = block.split('\n')
            header = lines[0]
            body = lines[1:]
            new_body = ["        from mavsdk.action import ActionError", "        try:"]
            for line in body:
                if line.strip():
                    new_body.append("    " + line)
            new_body.extend([
                "        except ActionError as e:",
                "            self.logger.error(f'MAVSDK ActionError in {m}: {e}')",
                "            raise"
            ])
            return header + '\n' + '\n'.join(new_body) + '\n'
        content = re.sub(pattern, replacer, content)

    # Same for _takeoff which takes arguments
    pattern_takeoff = r'(async def _takeoff\(self, altitude: float\):\n(?:.|\n)*?)(?=\n    def|\n    async def)'
    def replacer_takeoff(match):
        block = match.group(1)
        lines = block.split('\n')
        # We already injected the safety checks at the top of the method body in step 2.
        # But we still want to wrap the remaining action.takeoff in try except.
        # Let's just find the `await self._system.action.takeoff()` line and wrap it.
        # Actually, let's just do a simpler search and replace for the `await self._system.action.*` lines if we can.
        return block
    # Note: I'll just write a specific replacement for _takeoff
    takeoff_try = """        try:
            await self._system.action.set_takeoff_altitude(altitude)
            await self._system.action.takeoff()
            self._in_air = True
            async for in_air in self._system.telemetry.in_air():
                if in_air:
                    break
        except ActionError as e:
            self.logger.error(f"MAVSDK Takeoff ActionError: {e}")
            raise"""
    # Replace old takeoff body (after the safety checks we added)
    content = re.sub(r'        await self\._system\.action\.set_takeoff_altitude\(altitude\)\n        await self\._system\.action\.takeoff\(\)\n        self\._in_air = True\n        async for in_air in self\._system\.telemetry\.in_air\(\):\n            if in_air:\n                break', takeoff_try, content)


    with open(filename, 'w') as f:
        f.write(content)

refactor_file('simulation_backend.py')
refactor_file('real_backend.py')
