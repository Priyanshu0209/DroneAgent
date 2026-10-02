from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QPushButton, QGroupBox
from PySide6.QtCore import Qt

class MovementPanel(QWidget):
    def __init__(self, agent, parent=None):
        super().__init__(parent)
        self.agent = agent
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        group = QGroupBox("Movement Control")
        grid = QGridLayout()
        
        # Row 0
        self.btn_up = QPushButton("Up")
        self.btn_forward = QPushButton("Forward")
        self.btn_down = QPushButton("Down")
        grid.addWidget(self.btn_up, 0, 0)
        grid.addWidget(self.btn_forward, 0, 1)
        grid.addWidget(self.btn_down, 0, 2)
        
        # Row 1
        self.btn_left = QPushButton("Left")
        self.btn_hover = QPushButton("Hover")
        self.btn_right = QPushButton("Right")
        grid.addWidget(self.btn_left, 1, 0)
        grid.addWidget(self.btn_hover, 1, 1)
        grid.addWidget(self.btn_right, 1, 2)
        
        # Row 2
        self.btn_rot_left = QPushButton("Rotate Left")
        self.btn_backward = QPushButton("Backward")
        self.btn_rot_right = QPushButton("Rotate Right")
        grid.addWidget(self.btn_rot_left, 2, 0)
        grid.addWidget(self.btn_backward, 2, 1)
        grid.addWidget(self.btn_rot_right, 2, 2)
        
        # Row 3 (Action buttons)
        self.btn_stop = QPushButton("Stop")
        self.btn_brake = QPushButton("Brake")
        grid.addWidget(self.btn_stop, 3, 0, 1, 1)
        grid.addWidget(self.btn_brake, 3, 1, 1, 2)
        
        # Row 4 (Speed & adjustments)
        self.btn_inc_speed = QPushButton("Increase Speed")
        self.btn_dec_speed = QPushButton("Decrease Speed")
        grid.addWidget(self.btn_inc_speed, 4, 0, 1, 2)
        grid.addWidget(self.btn_dec_speed, 4, 2, 1, 1)
        
        # Row 5 (Altitude/Yaw increments)
        self.btn_alt_plus = QPushButton("Altitude +")
        self.btn_alt_minus = QPushButton("Altitude -")
        grid.addWidget(self.btn_alt_plus, 5, 0)
        grid.addWidget(self.btn_alt_minus, 5, 1)
        
        self.btn_yaw_plus = QPushButton("Yaw +")
        self.btn_yaw_minus = QPushButton("Yaw -")
        grid.addWidget(self.btn_yaw_plus, 6, 0)
        grid.addWidget(self.btn_yaw_minus, 6, 1)
        
        group.setLayout(grid)
        layout.addWidget(group)
        layout.addStretch()

        self._connect_signals()

    def _connect_signals(self):
        # Connect buttons to agent movement API
        self.btn_forward.clicked.connect(lambda: self.move("forward"))
        self.btn_backward.clicked.connect(lambda: self.move("backward"))
        self.btn_left.clicked.connect(lambda: self.move("left"))
        self.btn_right.clicked.connect(lambda: self.move("right"))
        self.btn_up.clicked.connect(lambda: self.move("up"))
        self.btn_down.clicked.connect(lambda: self.move("down"))
        self.btn_rot_left.clicked.connect(lambda: self.move("rotate_left"))
        self.btn_rot_right.clicked.connect(lambda: self.move("rotate_right"))
        self.btn_hover.clicked.connect(lambda: self.move("hover"))
        self.btn_stop.clicked.connect(lambda: self.move("stop"))
        self.btn_brake.clicked.connect(lambda: self.move("brake"))
        
        self.btn_inc_speed.clicked.connect(lambda: self.adjust_param("speed", 1))
        self.btn_dec_speed.clicked.connect(lambda: self.adjust_param("speed", -1))
        self.btn_alt_plus.clicked.connect(lambda: self.adjust_param("altitude", 1))
        self.btn_alt_minus.clicked.connect(lambda: self.adjust_param("altitude", -1))
        self.btn_yaw_plus.clicked.connect(lambda: self.adjust_param("yaw", 10))
        self.btn_yaw_minus.clicked.connect(lambda: self.adjust_param("yaw", -10))

    def move(self, direction):
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
            self.agent.logger.info(f"Adjusted GUI parameter {param} by {delta}")
