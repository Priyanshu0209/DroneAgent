from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QPushButton, QGroupBox, QRadioButton, QButtonGroup
from PySide6.QtCore import Qt

class SwarmPanel(QWidget):
    def __init__(self, agent, parent=None):
        super().__init__(parent)
        self.agent = agent
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Drone Selection
        group_sel = QGroupBox("Drone Selection")
        vbox_sel = QVBoxLayout()
        self.btn_group = QButtonGroup(self)
        
        self.radio_all = QRadioButton("All Drones")
        self.radio_all.setChecked(True)
        self.btn_group.addButton(self.radio_all, 0)
        vbox_sel.addWidget(self.radio_all)
        
        for i in range(1, 4):
            radio = QRadioButton(f"Drone{i}")
            self.btn_group.addButton(radio, i)
            vbox_sel.addWidget(radio)
            
        group_sel.setLayout(vbox_sel)
        layout.addWidget(group_sel)
        
        # Group Control
        group_ctrl = QGroupBox("Group Control")
        grid_ctrl = QGridLayout()
        
        self.btn_takeoff_all = QPushButton("Takeoff All")
        self.btn_land_all = QPushButton("Land All")
        self.btn_rtl_all = QPushButton("RTL All")
        self.btn_pause_all = QPushButton("Pause All")
        self.btn_resume_all = QPushButton("Resume All")
        self.btn_emergency_all = QPushButton("Emergency All")
        self.btn_emergency_all.setObjectName("btn_emergency") # Use styling
        
        grid_ctrl.addWidget(self.btn_takeoff_all, 0, 0)
        grid_ctrl.addWidget(self.btn_land_all, 0, 1)
        grid_ctrl.addWidget(self.btn_rtl_all, 1, 0)
        grid_ctrl.addWidget(self.btn_pause_all, 1, 1)
        grid_ctrl.addWidget(self.btn_resume_all, 2, 0)
        grid_ctrl.addWidget(self.btn_emergency_all, 2, 1)
        
        group_ctrl.setLayout(grid_ctrl)
        layout.addWidget(group_ctrl)
        layout.addStretch()
        
        # Connections
        self.btn_takeoff_all.clicked.connect(lambda: self.group_cmd("takeoff"))
        self.btn_land_all.clicked.connect(lambda: self.group_cmd("land"))
        self.btn_rtl_all.clicked.connect(lambda: self.group_cmd("rtl"))
        self.btn_pause_all.clicked.connect(lambda: self.group_cmd("pause"))
        self.btn_resume_all.clicked.connect(lambda: self.group_cmd("resume"))
        self.btn_emergency_all.clicked.connect(lambda: self.group_cmd("emergency"))
        
    def group_cmd(self, cmd):
        # Sends a broadcast or loops through known agents to issue group commands
        if hasattr(self.agent, 'communication') and self.agent.communication:
            self.agent.communication.broadcast_command(cmd)
            if hasattr(self.agent, 'logger'):
                self.agent.logger.info(f"Broadcasted swarm command: {cmd}")
