from PySide6.QtWidgets import (QWidget, QVBoxLayout, QComboBox, QFormLayout, 
                               QDoubleSpinBox, QPushButton, QGroupBox)

class FormationPanel(QWidget):
    def __init__(self, agent, parent=None):
        super().__init__(parent)
        self.agent = agent
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        group = QGroupBox("Formation Settings")
        form_layout = QFormLayout()
        
        # Formation selection
        self.combo_shape = QComboBox()
        formations = [
            "Line", "Column", "Triangle", "Diamond", "V", "Arrow", 
            "Echelon Left", "Echelon Right", "Circle", "Arc", "Fan", 
            "Orbit", "Spiral", "Custom"
        ]
        self.combo_shape.addItems(formations)
        
        # Parameters
        self.spin_spacing = QDoubleSpinBox()
        self.spin_spacing.setRange(1.0, 100.0)
        self.spin_spacing.setValue(5.0)
        
        self.spin_heading = QDoubleSpinBox()
        self.spin_heading.setRange(0.0, 360.0)
        self.spin_heading.setValue(0.0)
        
        self.spin_alt_offset = QDoubleSpinBox()
        self.spin_alt_offset.setRange(-50.0, 50.0)
        self.spin_alt_offset.setValue(0.0)
        
        self.spin_rotation = QDoubleSpinBox()
        self.spin_rotation.setRange(0.0, 360.0)
        self.spin_rotation.setValue(0.0)
        
        form_layout.addRow("Shape:", self.combo_shape)
        form_layout.addRow("Spacing (m):", self.spin_spacing)
        form_layout.addRow("Heading (deg):", self.spin_heading)
        form_layout.addRow("Alt Offset (m):", self.spin_alt_offset)
        form_layout.addRow("Rotation (deg):", self.spin_rotation)
        
        self.btn_apply = QPushButton("Apply Formation")
        form_layout.addRow(self.btn_apply)
        
        group.setLayout(form_layout)
        layout.addWidget(group)
        layout.addStretch()
        
        self.btn_apply.clicked.connect(self.apply_formation)
        
    def apply_formation(self):
        shape = self.combo_shape.currentText()
        spacing = self.spin_spacing.value()
        heading = self.spin_heading.value()
        alt_offset = self.spin_alt_offset.value()
        rotation = self.spin_rotation.value()
        
        
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

