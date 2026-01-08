"""
Campaign Calendar View
Visualizes campaigns on a calendar to detect overlaps and manage fleet schedule.
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QDateEdit, QLabel, QMessageBox, QComboBox, QGraphicsView,
                               QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem,
                               QScrollBar, QFrame, QMenu, QLineEdit)
from PyQt6.QtCore import Qt, QDate, QRectF
from PyQt6.QtGui import QColor, QBrush, QPen, QFont, QAction
import datetime
from src.data.campaign_storage import CampaignStorage
from src.data.vehicle_manager import VehicleManager
from src.data.distance_service import DistanceService

class CampaignCalendarView(QDialog):
    """Visual calendar for fleet management"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fleet Campaign Calendar")
        self.resize(1200, 800)
        
        self.storage = CampaignStorage()
        self.vehicle_manager = VehicleManager()
        self.distance_service = DistanceService()
        
        self.start_date = datetime.date.today()
        self.days_to_show = 30
        
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        # Date navigation
        prev_btn = QPushButton("<< Previous Month")
        prev_btn.clicked.connect(lambda: self.change_date(-30))
        toolbar.addWidget(prev_btn)
        
        self.date_label = QLabel()
        self.date_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        toolbar.addWidget(self.date_label)
        
        next_btn = QPushButton("Next Month >>")
        next_btn.clicked.connect(lambda: self.change_date(30))
        toolbar.addWidget(next_btn)
        
        toolbar.addStretch()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_data)
        toolbar.addWidget(refresh_btn)
        
        layout.addLayout(toolbar)
        
        # Calendar View
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        
        layout.addWidget(self.view)
        
        # Legend
        legend = QHBoxLayout()
        self.add_legend_item(legend, "Confirmed", "#FFC107") # Yellow
        self.add_legend_item(legend, "Reserved", "#FF9800")  # Orange
        self.add_legend_item(legend, "Canceled", "#795548")  # Brown
        self.add_legend_item(legend, "Transit", "#4CAF50")   # Green
        self.add_legend_item(legend, "Vehicle Issue", "#F44336") # Red
        self.add_legend_item(legend, "Conflict", "#E91E63")  # Pink
        legend.addStretch()
        layout.addLayout(legend)

    def contextMenuEvent(self, event):
        """Handle context menu for adding manual events"""
        # manual mapping of Y position to vehicle row
        # Header is 40, Row is 60.
        y = event.pos().y()
        HEADER_HEIGHT = 40
        ROW_HEIGHT = 60
        
        if y < HEADER_HEIGHT:
            return
            
        vehicle_idx = (y - HEADER_HEIGHT) // ROW_HEIGHT
        vehicles = self.vehicle_manager.get_active_vehicles()
        
        if 0 <= vehicle_idx < len(vehicles):
            vehicle = vehicles[vehicle_idx]
            menu = QMenu(self)
            
            add_maint = QAction("Add Vehicle Issue / Maintenance", self)
            add_maint.triggered.connect(lambda: self.add_manual_event(vehicle, "maintenance"))
            menu.addAction(add_maint)
            
            add_transit = QAction("Add Manual Transit", self)
            add_transit.triggered.connect(lambda: self.add_manual_event(vehicle, "manual_transit"))
            menu.addAction(add_transit)
            
            menu.exec(event.globalPos())

    def add_manual_event(self, vehicle, event_type):
        """Show dialog to add manual event"""
        from PyQt6.QtWidgets import QInputDialog, QDateEdit, QFormLayout, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Add {event_type.replace('_', ' ').capitalize()}")
        layout = QFormLayout(dialog)
        
        start_edit = QDateEdit()
        start_edit.setCalendarPopup(True)
        start_edit.setDate(QDate.currentDate())
        
        end_edit = QDateEdit()
        end_edit.setCalendarPopup(True)
        end_edit.setDate(QDate.currentDate())
        
        note_edit = QLineEdit()
        
        layout.addRow("Start Date:", start_edit)
        layout.addRow("End Date:", end_edit)
        layout.addRow("Details:", note_edit)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addWidget(btns)
        
        if dialog.exec():
            s_date = start_edit.date().toPyDate()
            e_date = end_edit.date().toPyDate()
            details = note_edit.text()
            
            if s_date > e_date:
                QMessageBox.warning(self, "Error", "Start date must be before end date")
                return
                
            success = self.vehicle_manager.add_schedule(vehicle['id'], s_date, e_date, event_type, details)
            if success:
                self.load_data()
            else:
                QMessageBox.critical(self, "Error", "Failed to save event.")

    def add_legend_item(self, layout, text, color):
        item = QHBoxLayout()
        box = QFrame()
        box.setFixedSize(16, 16)
        box.setStyleSheet(f"background-color: {color}; border: 1px solid #666;")
        item.addWidget(box)
        item.addWidget(QLabel(text))
        item.addSpacing(15)
        layout.addLayout(item)
        
    def change_date(self, days):
        self.start_date += datetime.timedelta(days=days)
        self.load_data()
        
    def _parse_time_range(self, time_str):
        """Parse HH:MM-HH:MM string into minutes tuple"""
        try:
            start, end = time_str.split('-')
            sh, sm = map(int, start.split(':'))
            eh, em = map(int, end.split(':'))
            return (sh * 60 + sm, eh * 60 + em)
        except:
            return (0, 1440) # Full day fallback

    def _check_time_overlap(self, range1, range2):
        """Check if two time ranges (minutes tuples) overlap"""
        start1, end1 = range1
        start2, end2 = range2
        return max(start1, start2) < min(end1, end2)

    def load_data(self):
        self.scene.clear()
        
        # Update label
        end_date = self.start_date + datetime.timedelta(days=self.days_to_show)
        self.date_label.setText(f"{self.start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}")
        
        # Get data
        campaigns = self.storage.get_all_campaigns()
        vehicles = self.vehicle_manager.get_active_vehicles()
        all_schedules = self.vehicle_manager.get_vehicle_schedules()
        
        # Constants
        ROW_HEIGHT = 60
        DAY_WIDTH = 40
        HEADER_HEIGHT = 40
        LABEL_WIDTH = 200
        
        # Draw Grid
        # Header (Dates)
        current = self.start_date
        for i in range(self.days_to_show):
            x = LABEL_WIDTH + i * DAY_WIDTH
            
            # Date text
            text = QGraphicsTextItem(current.strftime('%d\n%b'))
            text.setPos(x + 5, 5)
            self.scene.addItem(text)
            
            # Grid line
            line = self.scene.addLine(x, 0, x, HEADER_HEIGHT + len(vehicles) * ROW_HEIGHT, QPen(QColor("#ddd")))
            
            # Weekend highlight
            if current.weekday() >= 5:
                rect = QGraphicsRectItem(x, HEADER_HEIGHT, DAY_WIDTH, len(vehicles) * ROW_HEIGHT)
                rect.setBrush(QBrush(QColor("#f9f9f9")))
                rect.setPen(QPen(Qt.PenStyle.NoPen))
                self.scene.addItem(rect)
                rect.setZValue(-1)
                
            current += datetime.timedelta(days=1)
            
        # Draw Vehicles (Rows)
        for i, vehicle in enumerate(vehicles):
            y = HEADER_HEIGHT + i * ROW_HEIGHT
            
            # Vehicle Label
            label_bg = QGraphicsRectItem(0, y, LABEL_WIDTH, ROW_HEIGHT)
            label_bg.setBrush(QBrush(QColor("#eee")))
            label_bg.setPen(QPen(QColor("#ccc")))
            self.scene.addItem(label_bg)
            
            label_text = f"{vehicle['name']}\n{vehicle.get('registration', '')}"
            text = QGraphicsTextItem(label_text)
            text.setPos(10, y + 10)
            text.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            self.scene.addItem(text)
            
            # Driver info
            driver = vehicle.get('driver_name', 'No Driver')
            d_text = QGraphicsTextItem(driver)
            d_text.setPos(10, y + 35)
            d_text.setFont(QFont("Arial", 8))
            d_text.setDefaultTextColor(QColor("#666"))
            self.scene.addItem(d_text)
            
            # Horizontal line
            self.scene.addLine(0, y + ROW_HEIGHT, LABEL_WIDTH + self.days_to_show * DAY_WIDTH, y + ROW_HEIGHT, QPen(QColor("#ccc")))
            
            # 1. DRAW MANUAL SCHEDULES (Maintenance / Manual Transit)
            v_schedules = [s for s in all_schedules if s['vehicle_id'] == vehicle['id']]
            for sch in v_schedules:
                s_date = sch['start']
                e_date = sch['end']
                
                # Check overlap
                view_end = self.start_date + datetime.timedelta(days=self.days_to_show)
                if e_date < self.start_date or s_date >= view_end:
                    continue
                    
                start_offset = (s_date - self.start_date).days
                duration = (e_date - s_date).days + 1
                    
                draw_start = max(0, start_offset)
                draw_end = min(self.days_to_show, start_offset + duration)
                draw_width = draw_end - draw_start
                
                if draw_width <= 0: continue
                
                x = LABEL_WIDTH + draw_start * DAY_WIDTH
                w = draw_width * DAY_WIDTH
                
                rect = QGraphicsRectItem(x, y + 5, w, ROW_HEIGHT - 10) # Full height block
                
                # Color logic
                color = "#999"
                if sch['type'] in ['maintenance', 'no_docs', 'defective']:
                    color = "#F44336" # Red
                elif sch['type'] in ['transit', 'manual_transit']:
                    color = "#4CAF50" # Green (as requested)
                    
                rect.setBrush(QBrush(QColor(color)))
                rect.setPen(QPen(Qt.PenStyle.NoPen))
                rect.setOpacity(0.9) # High opacity to block beneath
                
                tooltip = f"{sch['type'].upper()}\n{sch['details']}\n{s_date} - {e_date}"
                rect.setToolTip(tooltip)
                self.scene.addItem(rect)
            
            # 2. DRAW CAMPAIGNS & TRANSIT & CONFLICTS
            vehicle_campaigns = [c for c in campaigns if c.get('vehicle_id') == vehicle['id']]
            
            # Pre-calculate conflicts
            # Conflict Rule: If ANY is exclusive, overlap on Date AND Time is a conflict.
            conflicting_ids = set()
            
            # Sort campaigns for transit check
            def get_camp_start(c):
                try:
                    return datetime.date.fromisoformat(str(c['start_date']))
                except:
                    return datetime.date.min
            vehicle_campaigns.sort(key=get_camp_start)
            
            # TRANSIT CHECK LOGIC (Auto)
            for j in range(len(vehicle_campaigns) - 1):
                c1 = vehicle_campaigns[j]
                c2 = vehicle_campaigns[j+1]
                
                c1_cities = [k for k in c1.get('city_periods', {}).keys() if k != '__meta__']
                c2_cities = [k for k in c2.get('city_periods', {}).keys() if k != '__meta__']
                if not c1_cities: c1_cities = c1.get('cities', [])
                if not c2_cities: c2_cities = c2.get('cities', [])
                
                if not c1_cities or not c2_cities: continue
                
                city_a = c1_cities[-1]
                city_b = c2_cities[0]
                
                if city_a == city_b: continue
                
                dist_km, time_h = self.distance_service.get_transit_info(city_a, city_b)
                if dist_km == 0: continue
                
                try:
                    end1 = datetime.date.fromisoformat(str(c1['end_date']))
                    start2 = datetime.date.fromisoformat(str(c2['start_date']))
                    
                    end1_h = self._parse_time_range(c1.get('daily_hours', '00:00-24:00'))[1] / 60
                    start2_h = self._parse_time_range(c2.get('daily_hours', '00:00-24:00'))[0] / 60
                    
                    days_gap = (start2 - end1).days
                    gap_hours = 0
                    if days_gap == 0: gap_hours = start2_h - end1_h
                    elif days_gap > 0: gap_hours = (days_gap - 1) * 24 + (24 - end1_h) + start2_h
                    
                    if gap_hours < time_h:
                        conflicting_ids.add(c1['id'])
                        conflicting_ids.add(c2['id'])
                    elif gap_hours < time_h + 24: 
                        # Draw AUTO TRANSIT Bar (Green)
                        c1_x_end = LABEL_WIDTH + ((end1 - self.start_date).days + 1) * DAY_WIDTH
                        tw = max(10, (time_h / 24) * DAY_WIDTH)
                        c2_x_start = LABEL_WIDTH + (start2 - self.start_date).days * DAY_WIDTH
                        if c1_x_end + tw > c2_x_start:
                             tw = max(5, c2_x_start - c1_x_end)
                        
                        tr = QGraphicsRectItem(c1_x_end, y + 20, tw, ROW_HEIGHT - 40)
                        tr.setBrush(QBrush(QColor("#4CAF50"))) # Green
                        tr.setToolTip(f"Auto Transit: {city_a} -> {city_b}\nDist: {dist_km} km\nEst: {time_h} hours")
                        self.scene.addItem(tr)
                except Exception as e:
                    pass

            # Conflict Detection Loop
            for c1 in vehicle_campaigns:
                for c2 in vehicle_campaigns:
                    if c1['id'] == c2['id']: continue
                    try:
                        s1 = datetime.date.fromisoformat(str(c1['start_date']))
                        e1 = datetime.date.fromisoformat(str(c1['end_date']))
                        s2 = datetime.date.fromisoformat(str(c2['start_date']))
                        e2 = datetime.date.fromisoformat(str(c2['end_date']))
                        
                        if max(s1, s2) <= min(e1, e2): # Dates overlap
                            hours1 = c1.get('daily_hours', '00:00-24:00')
                            hours2 = c2.get('daily_hours', '00:00-24:00')
                            t1 = self._parse_time_range(hours1)
                            t2 = self._parse_time_range(hours2)
                            
                            if self._check_time_overlap(t1, t2):
                                excl1 = c1.get('is_exclusive', False)
                                excl2 = c2.get('is_exclusive', False)
                                if str(excl1).lower() == 'true': excl1 = True
                                if str(excl2).lower() == 'true': excl2 = True
                                
                                if excl1 or excl2:
                                    conflicting_ids.add(c1['id'])
                                    conflicting_ids.add(c2['id'])
                    except Exception as e: pass
            
            # Draw Campaigns
            for camp in vehicle_campaigns:
                intervals = []
                
                city_periods = camp.get('city_periods', {})
                all_cities = [c for c in city_periods.keys() if c != '__meta__']
                has_periods = False
                
                if isinstance(city_periods, dict) and city_periods:
                    cities = [c for c in city_periods.keys() if c != '__meta__']
                    for city in cities:
                        p_data = city_periods[city]
                        if isinstance(p_data, list):
                            for p in p_data:
                                if isinstance(p, dict):
                                    try:
                                        s = datetime.date.fromisoformat(str(p.get('start')))
                                        e = datetime.date.fromisoformat(str(p.get('end')))
                                        intervals.append((s, e, city))
                                        has_periods = True
                                    except: pass
                        elif isinstance(p_data, dict):
                            try:
                                s = datetime.date.fromisoformat(str(p_data.get('start')))
                                e = datetime.date.fromisoformat(str(p_data.get('end')))
                                intervals.append((s, e, city))
                                has_periods = True
                            except: pass

                if not has_periods:
                    try:
                        c_start = datetime.date.fromisoformat(str(camp['start_date']))
                        c_end = datetime.date.fromisoformat(str(camp['end_date']))
                        intervals.append((c_start, c_end, "General"))
                    except: continue
                
                for c_start, c_end, loc_label in intervals:
                    view_end = self.start_date + datetime.timedelta(days=self.days_to_show)
                    if c_end < self.start_date or c_start >= view_end: continue
                        
                    start_offset = (c_start - self.start_date).days
                    duration = (c_end - c_start).days + 1
                    draw_start = max(0, start_offset)
                    draw_end = min(self.days_to_show, start_offset + duration)
                    draw_width = draw_end - draw_start
                    
                    if draw_width <= 0: continue
                    
                    x = LABEL_WIDTH + draw_start * DAY_WIDTH
                    w = draw_width * DAY_WIDTH
                    
                    rect = QGraphicsRectItem(x, y + 15, w, ROW_HEIGHT - 30) # Slightly smaller than issues
                    
                    # COLOR LOGIC
                    raw_status = camp.get('status')
                    status = raw_status.lower() if raw_status else 'confirmed'
                    
                    if camp.get('id') in conflicting_ids:
                        color = "#E91E63" # Pink Conflict
                    elif status == 'confirmed':
                        color = "#FFC107" # Yellow
                    elif status == 'reserved':
                        color = "#FF9800" # Orange
                    elif status == 'canceled':
                        color = "#795548" # Brown
                    else:
                        color = "#4CAF50" # Default Green (or should be yellow default?) 
                        # User said "Confirmed = Yellow". If Status missing, assume Confirmed?
                        # Let's assume Confirm = Yellow.
                        color = "#FFC107"
                        
                    rect.setBrush(QBrush(QColor(color)))
                    rect.setPen(QPen(Qt.PenStyle.NoPen))
                    rect.setOpacity(0.8)
                    
                    # Tooltip
                    client = camp.get('client_name', 'Unknown')
                    name = camp.get('campaign_name', 'Campaign')
                    hours = camp.get('daily_hours', 'N/A')
                    cities_str = ", ".join(all_cities) if all_cities else "General"
                    tooltip = (f"Client: {client}\nCampaign: {name}\nStatus: {status.capitalize()}\n"
                               f"Cities: {cities_str}\nHours: {hours}\nActive: {c_start} to {c_end}")
                    rect.setToolTip(tooltip)
                    
                    self.scene.addItem(rect)
                    
                    label_text = client
                    if loc_label != "General": label_text += f" ({loc_label})"
                    c_text = QGraphicsTextItem(label_text)
                    c_text.setPos(x + 5, y + 20)
                    c_text.setDefaultTextColor(Qt.GlobalColor.black) # Yellow bg needs black text usually
                    
                    if c_text.boundingRect().width() > w:
                        dots = ".."
                        available = int(w / 8)
                        if available > 2: short_text = label_text[:available-2] + dots
                        else: short_text = ""
                        c_text.setPlainText(short_text)
                        
                    if w > 20: self.scene.addItem(c_text)
