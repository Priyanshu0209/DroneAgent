from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLabel, QGroupBox
from PySide6.QtCore import QTimer

class TelemetryPanel(QWidget):
    def __init__(self, agent, parent=None):
        super().__init__(parent)
        self.agent = agent
        self.labels = {}
        self.init_ui()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start(500) # Update at 2Hz
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        group = QGroupBox("Live Telemetry")
        form = QFormLayout()
        
        fields = [
            "Battery", "GPS", "Latitude", "Longitude", "Altitude", 
            "Velocity", "Heading", "Mode", "Health", "RSSI", 
            "Heartbeat", "Neighbor Count"
        ]
        
        for field in fields:
            label = QLabel("N/A")
            # Style values slightly differently to stand out
            label.setStyleSheet("color: #4da6ff; font-weight: bold;")
            form.addRow(f"{field}:", label)
            self.labels[field] = label
            
        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()
        
    def update_telemetry(self):
        if not self.agent:
            return
            
        try:
            # Gather state from agent subsystems
            import math
            if hasattr(self.agent, 'telemetry') and self.agent.telemetry:
                batt = self.agent.telemetry.get_battery()
                if batt is not None:
                    self.labels["Battery"].setText(f"{batt * 100:.1f} %")
                
                gps = self.agent.telemetry.get_gps()
                if gps:
                    self.labels["Latitude"].setText(f"{gps[0]:.6f}")
                    self.labels["Longitude"].setText(f"{gps[1]:.6f}")
                    self.labels["Altitude"].setText(f"{gps[2]:.2f} m")
                
                vel = self.agent.telemetry.get_velocity()
                if vel:
                    speed = math.sqrt(vel[0]**2 + vel[1]**2 + vel[2]**2)
                    self.labels["Velocity"].setText(f"{speed:.2f} m/s")
                
                heading = self.agent.telemetry.get_heading()
                if heading is not None:
                    self.labels["Heading"].setText(f"{math.degrees(heading):.1f} deg")
                
            if hasattr(self.agent, 'state_machine') and self.agent.state_machine:
                state = self.agent.state_machine.get_state()
                self.labels["Mode"].setText(str(state.name if state else "UNKNOWN"))
                
            if hasattr(self.agent, 'communication') and self.agent.communication:
                count = len(self.agent.communication.get_neighbor_list())
                self.labels["Neighbor Count"].setText(str(count))
                
            # RSSI, Health, Heartbeat could come from communication/heartbeat modules
            self.labels["GPS"].setText("3D Fix") # Placeholder
            self.labels["Health"].setText("OK")
            self.labels["RSSI"].setText("-65 dBm")
            
        except Exception:
            pass # Fail gracefully if agent is shutting down or state is unavailable
