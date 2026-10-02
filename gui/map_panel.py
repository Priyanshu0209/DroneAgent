from PySide6.QtWidgets import QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QGroupBox, QHBoxLayout, QCheckBox
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QPolygonF
import math

class MapPanel(QWidget):
    def __init__(self, agent, parent=None):
        super().__init__(parent)
        self.agent = agent
        self.init_ui()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_map)
        self.timer.start(500)
        
        self.drone_trails = {} # drone_id -> list of QPointF
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        group = QGroupBox("Swarm Map")
        vbox = QVBoxLayout()
        
        # Checkboxes for toggling overlays
        hbox = QHBoxLayout()
        self.cb_drones = QCheckBox("Drone Positions")
        self.cb_drones.setChecked(True)
        self.cb_trails = QCheckBox("GPS Trail")
        self.cb_trails.setChecked(True)
        self.cb_links = QCheckBox("Neighbor Links")
        self.cb_links.setChecked(True)
        self.cb_radius = QCheckBox("Collision Radius")
        
        hbox.addWidget(self.cb_drones)
        hbox.addWidget(self.cb_trails)
        hbox.addWidget(self.cb_links)
        hbox.addWidget(self.cb_radius)
        vbox.addLayout(hbox)
        
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        # Assuming origin is center, scale arbitrary pixels to meters roughly
        self.view.setSceneRect(-500, -500, 1000, 1000)
        
        vbox.addWidget(self.view)
        group.setLayout(vbox)
        layout.addWidget(group)
        
    def update_map(self):
        self.scene.clear()
        
        # Draw axes/grid (optional, simplified)
        pen_grid = QPen(QColor(50, 50, 50))
        self.scene.addLine(-500, 0, 500, 0, pen_grid)
        self.scene.addLine(0, -500, 0, 500, pen_grid)
        
        if not self.agent:
            return
            
        if not hasattr(self.agent, 'telemetry') or not self.agent.telemetry:
            txt = self.scene.addText("No Telemetry")
            from PySide6.QtGui import QFont
            txt.setFont(QFont("Arial", 16, QFont.Bold))
            txt.setDefaultTextColor(Qt.red)
            txt.setPos(-50, -10)
            return
            
        # Draw elements based on backend data
        # Note: In a real system, you'd translate lat/lon to local cartesian (x,y)
        # We assume local coordinate system for rendering here.
        drones = {} # e.g. {1: {'x': 0, 'y': 0, 'heading': 0}}
        
        # Add self to drones dict
        my_id = self.agent.config.get('drone_id', 1) if self.agent.config else 1
        my_x, my_y = 0.0, 0.0
        
        try:
            state = self.agent.telemetry.get_state()
            # Faux projection for rendering
            lat = state.get('latitude', 0.0)
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
            my_y = (lat - home_lat) * 111000
            drones[my_id] = {'x': my_x, 'y': my_y, 'heading': state.get('heading', 0.0)}
        except Exception:
            # Fallback if telemetry errors out for any reason
            pass
            
        # Add neighbors safely
        if hasattr(self.agent, 'neighbor') and self.agent.neighbor:
            try:
                active_neighbors = self.agent.neighbor.get_active_neighbors()
                for n_id, packet in active_neighbors.items():
                    nx = (packet.gps_lon - home_lon) * 111000 * math.cos(math.radians(home_lat))
                    ny = (packet.gps_lat - home_lat) * 111000
                    drones[n_id] = {'x': nx, 'y': ny, 'heading': packet.heading}
            except Exception:
                pass
                    
        # Update trails
        for d_id, d_pos in drones.items():
            if d_id not in self.drone_trails:
                self.drone_trails[d_id] = []
            pt = QPointF(d_pos['x'], -d_pos['y']) # Qt y is down
            self.drone_trails[d_id].append(pt)
            if len(self.drone_trails[d_id]) > 100:
                self.drone_trails[d_id].pop(0)
                
        # Draw links
        if self.cb_links.isChecked():
            pen_link = QPen(QColor(0, 150, 255, 100), 2, Qt.DashLine)
            for d_id, pos1 in drones.items():
                for other_id, pos2 in drones.items():
                    if d_id < other_id:
                        self.scene.addLine(pos1['x'], -pos1['y'], pos2['x'], -pos2['y'], pen_link)
                        
        # Draw trails
        if self.cb_trails.isChecked():
            pen_trail = QPen(QColor(150, 150, 150, 150), 1)
            for d_id, trail in self.drone_trails.items():
                for i in range(1, len(trail)):
                    self.scene.addLine(trail[i-1].x(), trail[i-1].y(), trail[i].x(), trail[i].y(), pen_trail)
                    
        # Draw collision radius
        if self.cb_radius.isChecked():
            radius = self.agent.config.get('collision_radius', 5.0)
            pen_rad = QPen(QColor(255, 100, 100, 150), 1, Qt.DotLine)
            brush_rad = QBrush(QColor(255, 100, 100, 30))
            for d_id, pos in drones.items():
                self.scene.addEllipse(pos['x'] - radius, -pos['y'] - radius, radius*2, radius*2, pen_rad, brush_rad)
                
        # Draw drones
        if self.cb_drones.isChecked():
            pen_drone = QPen(Qt.black, 1)
            for d_id, pos in drones.items():
                brush = QBrush(QColor(0, 200, 0) if d_id == my_id else QColor(200, 100, 0))
                
                # Draw triangle for drone heading
                poly = QPolygonF()
                size = 10
                poly.append(QPointF(0, -size))
                poly.append(QPointF(-size*0.8, size))
                poly.append(QPointF(size*0.8, size))
                
                item = self.scene.addPolygon(poly, pen_drone, brush)
                item.setPos(pos['x'], -pos['y'])
                item.setRotation(pos['heading'])
                
                # Text label
                txt = self.scene.addText(f"D{d_id}")
                txt.setDefaultTextColor(Qt.white)
                txt.setPos(pos['x'] + 5, -pos['y'] + 5)
