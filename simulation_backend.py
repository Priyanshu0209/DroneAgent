import asyncio
import logging
import time
import threading
import subprocess
import os
import sys
import shutil
from typing import Optional, Tuple
import mavsdk
from mavsdk import offboard
from mavsdk.action import ActionError
from mavsdk.offboard import OffboardError, PositionNedYaw, VelocityNedYaw

from backend import HardwareInterface

class SimulationBackend(HardwareInterface):
    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config
        self.logger = logger.getChild("SimulationBackend")
        self.drone_id = config.get('drone_id', 1)
        
        # We must bind mavsdk.System() to the thread's event loop.
        # Since __init__ runs on main thread but methods run on SimBackend thread,
        # we pre-create the loop here and temporarily set it.
        self._loop_instance = asyncio.new_event_loop()
        
        old_loop = None
        try:
            old_loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
            
        asyncio.set_event_loop(self._loop_instance)
        
        # Check if gRPC server is already listening on localhost:50051
        import socket
        self.grpc_port = 50051
        server_running = False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', self.grpc_port)) == 0:
                server_running = True
                
        # Read simulation specific connection from config
        conn_config = config.get('connection', {})
        if 'type' not in conn_config or 'url' not in conn_config:
            raise ValueError("connection.type or connection.url is missing in configuration")
        self.connection_type = conn_config["type"]
        self.connection_url = conn_config["url"]
        
        self._server_process = None
                
        if server_running:
            self.logger.info("Existing MAVSDK server detected.")
            self._use_existing_server = True
            self._embedded_server = False
        else:
            self.logger.info("Embedded MAVSDK server will be started.")
            self._use_existing_server = False
            self._embedded_server = True
            
        self._system = mavsdk.System(mavsdk_server_address="localhost", port=self.grpc_port)
            
        if old_loop:
            asyncio.set_event_loop(old_loop)
            
        self._connected = False
        self._armed = False
        self._in_air = False
        self._offboard_active = False
        self._telemetry_task = None
        self._offboard_task = None
        self._connection_task = None
        self._stop_event = asyncio.Event()
        self._thread = None
        self._position_setpoint = None
        self._velocity_setpoint = None
    
    @property
    def drone(self):
        return self._system
        
    @property
    def loop(self):
        return self._loop_instance

    def is_connected(self) -> bool:
        return self._connected

    def is_armed(self) -> bool:
        return self._armed
        
    def is_in_air(self) -> bool:
        return self._in_air
        
    def is_offboard_active(self) -> bool:
        return self._offboard_active

    async def _connect(self):
        max_retries = 5
        retry_delay = 2.0
        
        if not self._use_existing_server:
            # Locate mavsdk_server
            mavsdk_server_path = shutil.which("mavsdk_server")
            if not mavsdk_server_path:
                # Try finding it in the mavsdk package
                try:
                    import mavsdk.bin
                    mavsdk_server_path = os.path.join(os.path.dirname(mavsdk.bin.__file__), "mavsdk_server")
                    if not os.path.exists(mavsdk_server_path) and sys.platform.startswith('linux'):
                        # maybe with _musl or _glibc extension in some older versions
                        import glob
                        matches = glob.glob(mavsdk_server_path + "*")
                        if matches:
                            mavsdk_server_path = matches[0]
                except ImportError:
                    pass
            
            if not mavsdk_server_path or not os.path.exists(mavsdk_server_path):
                self.logger.error("Could not find mavsdk_server executable. Is MAVSDK installed?")
                return
                
            self.logger.info(f"Launching embedded MAVSDK server subprocess: {mavsdk_server_path}")
            self._server_process = subprocess.Popen(
                [mavsdk_server_path, "-p", str(self.grpc_port), self.connection_url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for process startup
            await asyncio.sleep(1.0)
            
            if self._server_process.poll() is not None:
                self.logger.error("Embedded MAVSDK server failed to start or crashed immediately.")
                return
                
            try:
                self.logger.info("Attempting System.connect() to embedded server")
                await asyncio.wait_for(self._system.connect(), timeout=5.0)
            except asyncio.TimeoutError:
                self.logger.error("Timeout: MAVSDK System failed to connect to embedded server")
                return
            except Exception as e:
                self.logger.error(f"Failed to connect to MAVSDK server: {e}")
                return
        else:
            self.logger.info("Connecting to existing MAVSDK server")
            
        for attempt in range(max_retries):
            self.logger.info("Waiting connection")
            discovered = False
            try:
                async def wait_for_discovery():
                    async for state in self._system.core.connection_state():
                        if state.is_connected:
                            return True
                    return False
                discovered = await asyncio.wait_for(wait_for_discovery(), timeout=10.0)
            except asyncio.TimeoutError:
                self.logger.warning("Connection state check timed out.")
            except Exception as e:
                self.logger.error(f"Connection state error: {e}")
                
            if discovered:
                if not self._use_existing_server:
                    self.logger.info("Embedded server started successfully and is accepting connections.")
                self.logger.info("Connection established")
                self.logger.info("Health received")
                
                healthy = False
                try:
                    async def wait_for_health():
                        async for health in self._system.telemetry.health():
                            if health.is_global_position_ok and health.is_home_position_ok:
                                return True
                        return False
                    healthy = await asyncio.wait_for(wait_for_health(), timeout=20.0)
                except asyncio.TimeoutError:
                    self.logger.warning("Health check timed out.")
                except Exception as e:
                    self.logger.error(f"Health check error: {e}")
                    
                if healthy:
                    self.logger.info("GPS OK")
                    self.logger.info("Global position OK")
                    self.logger.info("Ready")
                    self._connected = True
                    return
                else:
                    self.logger.warning("Health conditions not met.")
                    
            if attempt < max_retries - 1:
                self.logger.info("Retrying connection...")
                await asyncio.sleep(retry_delay)
                
        self.logger.error("Failed to connect to SITL simulation after maximum retries.")

    def connect(self) -> bool:
        self.logger.info("Connecting SimulationBackend...")
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="SimBackend")
            self._thread.start()
        
        # Wait until connected to prevent telemetry plugin errors
        start_time = time.time()
        timeout = 60.0
        while not self.is_connected() and time.time() - start_time < timeout:
            if not self._thread.is_alive():
                break
            time.sleep(0.1)
            
        if self.is_connected():
            self.logger.info("SimulationBackend successfully connected to MAVSDK.")
            return True
        else:
            self.logger.error("SimulationBackend connection failed.")
            self.stop()
            return False
            
    def reconnect(self) -> bool:
        self.logger.warning("Reconnecting SimulationBackend...")
        self.stop()
        
        # Recreate event loop to cleanly reset grpc channels
        self._connected = False
        self._armed = False
        self._in_air = False
        self._offboard_active = False
        self._telemetry_task = None
        self._offboard_task = None
        self._connection_task = None
        self._position_setpoint = None
        self._velocity_setpoint = None
        
        self._loop_instance = asyncio.new_event_loop()
        old_loop = None
        try:
            old_loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
            
        asyncio.set_event_loop(self._loop_instance)
        
        import socket
        server_running = False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', self.grpc_port)) == 0:
                server_running = True
                
        if server_running:
            self.logger.info("Existing MAVSDK server detected.")
            self._use_existing_server = True
            self._embedded_server = False
        else:
            self.logger.info("Embedded MAVSDK server will be started.")
            self._use_existing_server = False
            self._embedded_server = True
        
        self._system = mavsdk.System(mavsdk_server_address="localhost", port=self.grpc_port)
        self._stop_event = asyncio.Event()
            
        if old_loop:
            asyncio.set_event_loop(old_loop)
            
        return self.connect()
        
    def _run_loop(self):
        asyncio.set_event_loop(self._loop_instance)
        self._loop_instance.run_until_complete(self._main())
        
    async def _main(self):
        await self._connect()
        if self._connected:
            self._telemetry_task = self._loop_instance.create_task(self._telemetry_loop())
            await self._stop_event.wait()
            if self._telemetry_task:
                self._telemetry_task.cancel()
            if self._offboard_task:
                self._offboard_task.cancel()

    def stop(self):
        self.logger.info("Stopping SimulationBackend...")
        if self._loop_instance and self._loop_instance.is_running():
            self._loop_instance.call_soon_threadsafe(self._stop_event.set)
        if self._thread:
            self._thread.join(timeout=5.0)
            
        if self._server_process is not None:
            self.logger.info("Terminating embedded MAVSDK server subprocess...")
            self._server_process.terminate()
            try:
                self._server_process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._server_process.kill()
            self._server_process = None

    async def _telemetry_loop(self):
        while not self._stop_event.is_set():
            try:
                async for battery in self._system.telemetry.battery():
                    self.logger.debug(f"Sim Battery: {battery.remaining_percent * 100:.1f}%")
                    break
            except Exception as e:
                self.logger.error(f"Telemetry error: {e}")
            await asyncio.sleep(1.0)

    def arm(self):
        self.logger.info("Arming simulation drone...")
        try:
            return asyncio.run_coroutine_threadsafe(self._arm(), self._loop_instance)
        except Exception as e:
            self.logger.error(f"Failed to arm: {e}")
            raise

    async def _arm(self):
        from mavsdk.action import ActionError
        try:
            await self._system.action.arm()
            self._armed = True
        except ActionError as e:
            self.logger.error(f'MAVSDK ActionError in {m}: {e}')
            raise

    def disarm(self):
        self.logger.info("Disarming simulation drone...")
        try:
            return asyncio.run_coroutine_threadsafe(self._disarm(), self._loop_instance)
        except Exception as e:
            self.logger.error(f"Failed to disarm: {e}")
            raise

    async def _disarm(self):
        from mavsdk.action import ActionError
        try:
            await self._system.action.disarm()
            self._armed = False
        except ActionError as e:
            self.logger.error(f'MAVSDK ActionError in {m}: {e}')
            raise

    def takeoff(self, altitude: float):
        self.logger.info(f"Taking off in simulation to {altitude}m...")
        try:
            return asyncio.run_coroutine_threadsafe(self._takeoff(altitude), self._loop_instance)
        except Exception as e:
            self.logger.error(f"Takeoff failed: {e}")
            raise

    async def _takeoff(self, altitude: float):
        from mavsdk.action import ActionError
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

        try:
            await self._system.action.set_takeoff_altitude(altitude)
            await self._system.action.takeoff()
            self._in_air = True
            async for in_air in self._system.telemetry.in_air():
                if in_air:
                    break
        except ActionError as e:
            self.logger.error(f"MAVSDK Takeoff ActionError: {e}")
            raise

    def land(self):
        self.logger.info("Landing simulation drone...")
        try:
            return asyncio.run_coroutine_threadsafe(self._land(), self._loop_instance)
        except Exception as e:
            self.logger.error(f"Land failed: {e}")
            raise

    async def _land(self):
        from mavsdk.action import ActionError
        try:
            await self._system.action.land()
            self._in_air = False
            async for in_air in self._system.telemetry.in_air():
                if not in_air:
                    break
        except ActionError as e:
            self.logger.error(f'MAVSDK ActionError in {m}: {e}')
            raise

    def return_to_launch(self):
        self.logger.info("Simulation returning to launch...")
        try:
            return asyncio.run_coroutine_threadsafe(self._return_to_launch(), self._loop_instance)
        except Exception as e:
            self.logger.error(f"RTL failed: {e}")
            raise

    async def _return_to_launch(self):
        from mavsdk.action import ActionError
        try:
            if self._offboard_active:
                await self._system.offboard.stop()
                self._offboard_active = False
                if self._offboard_task:
                    self._offboard_task.cancel()
                    self._offboard_task = None
            
            self._position_setpoint = None
            self._velocity_setpoint = None

            await self._system.action.return_to_launch()
        except ActionError as e:
            self.logger.error(f'MAVSDK ActionError in _return_to_launch: {e}')
            raise

    def set_offboard_mode(self):
        self.logger.info("Setting offboard mode in simulation...")
        try:
            return asyncio.run_coroutine_threadsafe(self._set_offboard_mode(), self._loop_instance)
        except Exception as e:
            self.logger.error(f"Failed to set offboard mode: {e}")
            raise

    async def _set_offboard_mode(self):
        await self._system.offboard.set_position_ned(PositionNedYaw(0.0, 0.0, 0.0, 0.0))
        await self._system.offboard.start()
        self._offboard_active = True
        if self._offboard_task is None or self._offboard_task.done():
            self._offboard_task = self._loop_instance.create_task(self._offboard_control_loop())

    def offboard_stop(self):
        self.logger.info("Stopping offboard mode in simulation...")
        try:
            return asyncio.run_coroutine_threadsafe(self._offboard_stop(), self._loop_instance)
        except Exception as e:
            self.logger.error(f"Failed to stop offboard mode: {e}")
            raise

    async def _offboard_stop(self):
        await self._system.offboard.stop()
        self._offboard_active = False
        if self._offboard_task:
            self._offboard_task.cancel()
            self._offboard_task = None

    def emergency_stop(self):
        self.logger.warning("SIMULATION EMERGENCY STOP!")
        try:
            return asyncio.run_coroutine_threadsafe(self._emergency_stop(), self._loop_instance)
        except Exception as e:
            self.logger.error(f"Emergency stop failed: {e}")
            raise

    async def _emergency_stop(self):
        from mavsdk.action import ActionError
        try:
            await self._system.action.kill()
            self._armed = False
            self._in_air = False
            self._offboard_active = False
        except ActionError as e:
            self.logger.error(f'MAVSDK ActionError in {m}: {e}')
            raise

    def failsafe(self):
        self.logger.warning("SIMULATION FAILSAFE activated")
        self.return_to_launch()


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

    def set_position_ned(self, north: float, east: float, down: float, yaw_deg: float = 0.0):
        # Buffer setpoint even if offboard not fully active yet
        if not self._offboard_active:
            self.logger.debug("Offboard not fully active, buffering position setpoint")
        self._position_setpoint = (north, east, down, yaw_deg)
        self._velocity_setpoint = None
        self.logger.info(f"Position command stored: {self._position_setpoint}")

    def set_velocity_ned(self, north_m_s: float, east_m_s: float, down_m_s: float, yaw_deg: float = 0.0):
        if not self._offboard_active:
            self.logger.debug("Offboard not fully active, buffering velocity setpoint")
        self._velocity_setpoint = (north_m_s, east_m_s, down_m_s, yaw_deg)
        self._position_setpoint = None
        self.logger.info(f"Velocity command stored: {self._velocity_setpoint}")

    async def _offboard_control_loop(self):
        self.logger.info("Starting simulation offboard control loop")
        try:
            while not self._stop_event.is_set() and self._offboard_active:
                setpoint_type = "None"
                if self._position_setpoint is not None:
                    setpoint_type = "Position"
                    north, east, down, yaw_deg = self._position_setpoint
                    await self._system.offboard.set_position_ned(
                        PositionNedYaw(north, east, down, yaw_deg)
                    )
                    self.logger.debug(f"Position command published: {self._position_setpoint}")
                elif self._velocity_setpoint is not None:
                    setpoint_type = "Velocity"
                    north, east, down, yaw_deg = self._velocity_setpoint
                    await self._system.offboard.set_velocity_ned(
                        VelocityNedYaw(north, east, down, yaw_deg)
                    )
                    self.logger.debug(f"Velocity command published: {self._velocity_setpoint}")
                else:
                    setpoint_type = "Hold/Zero Position"
                    await self._system.offboard.set_position_ned(
                        PositionNedYaw(0.0, 0.0, 0.0, 0.0)
                    )
                    self.logger.debug("Zero position command published")
                
                self.logger.debug(f"Current Offboard mode: {self._offboard_active}, Current manual override: N/A, Current setpoint type: {setpoint_type}")
                await asyncio.sleep(0.02)
        except OffboardError as e:
            self.logger.error(f"Offboard error: {e}")
            self._offboard_active = False
        except Exception as e:
            self.logger.error(f"Offboard loop error: {e}")
