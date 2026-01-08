from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                              QTableWidgetItem, QPushButton, QMessageBox, QHeaderView,
                              QInputDialog, QComboBox, QDateEdit, QDoubleSpinBox, QFormLayout,
                              QDialogButtonBox, QLabel)
from PyQt6.QtCore import QDate
import json
import os
import datetime

class EventEditorDialog(QDialog):
    """Dialog for adding/editing a single event"""
    def __init__(self, parent=None, city="", event_key=None, event_data=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Event" if event_data else "Add Event")
        self.resize(500, 450)
        
        layout = QFormLayout(self)
        
        # Event Name
        self.event_name_input = QLineEdit()
        if event_data:
            self.event_name_input.setText(event_data.get('name', ''))
        layout.addRow("Event Name:", self.event_name_input)
        
        # Start Date
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        if event_data and 'start_date' in event_data:
            date_obj = datetime.datetime.strptime(event_data['start_date'], '%Y-%m-%d').date()
            qdate = QDate(date_obj.year, date_obj.month, date_obj.day)
            self.start_date_edit.setDate(qdate)
        elif event_key:
            # Legacy: single date stored as key
            date_obj = datetime.datetime.strptime(event_key, '%Y-%m-%d').date()
            qdate = QDate(date_obj.year, date_obj.month, date_obj.day)
            self.start_date_edit.setDate(qdate)
        else:
            self.start_date_edit.setDate(QDate.currentDate())
        layout.addRow("Start Date:", self.start_date_edit)
        
        # End Date
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        if event_data and 'end_date' in event_data:
            date_obj = datetime.datetime.strptime(event_data['end_date'], '%Y-%m-%d').date()
            qdate = QDate(date_obj.year, date_obj.month, date_obj.day)
            self.end_date_edit.setDate(qdate)
        else:
            self.end_date_edit.setDate(self.start_date_edit.date())
        layout.addRow("End Date:", self.end_date_edit)
        
        # Single Day Checkbox
        from PyQt6.QtWidgets import QCheckBox
        self.single_day_check = QCheckBox("Single Day Event")
        self.single_day_check.setChecked(event_data.get('is_single_day', True) if event_data else True)
        self.single_day_check.toggled.connect(self.toggle_end_date)
        layout.addRow("", self.single_day_check)
        
        # Time Range (optional)
        time_layout = QHBoxLayout()
        from PyQt6.QtWidgets import QTimeEdit
        from PyQt6.QtCore import QTime
        
        self.time_start_edit = QTimeEdit()
        self.time_start_edit.setDisplayFormat("HH:mm")
        if event_data and 'time_start' in event_data:
            time_obj = datetime.datetime.strptime(event_data['time_start'], '%H:%M').time()
            self.time_start_edit.setTime(QTime(time_obj.hour, time_obj.minute))
        else:
            self.time_start_edit.setTime(QTime(0, 0))
        time_layout.addWidget(QLabel("From:"))
        time_layout.addWidget(self.time_start_edit)
        
        self.time_end_edit = QTimeEdit()
        self.time_end_edit.setDisplayFormat("HH:mm")
        if event_data and 'time_end' in event_data:
            time_obj = datetime.datetime.strptime(event_data['time_end'], '%H:%M').time()
            self.time_end_edit.setTime(QTime(time_obj.hour, time_obj.minute))
        else:
            self.time_end_edit.setTime(QTime(23, 59))
        time_layout.addWidget(QLabel("To:"))
        time_layout.addWidget(self.time_end_edit)
        
        layout.addRow("Time Range (optional):", time_layout)
        
        # Location
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("e.g., Piata Unirii, Centru Vechi, Strada Republicii")
        if event_data:
            self.location_input.setText(event_data.get('location', ''))
        layout.addRow("Location (optional):", self.location_input)
        
        # Traffic Multiplier
        self.traffic_mult = QDoubleSpinBox()
        self.traffic_mult.setRange(0.1, 10.0)
        self.traffic_mult.setSingleStep(0.1)
        self.traffic_mult.setValue(event_data.get('traffic_multiplier', 1.0) if event_data else 1.0)
        self.traffic_mult.setDecimals(1)
        layout.addRow("Traffic Multiplier:", self.traffic_mult)
        
        # Pedestrian Multiplier
        self.pedestrian_mult = QDoubleSpinBox()
        self.pedestrian_mult.setRange(0.1, 10.0)
        self.pedestrian_mult.setSingleStep(0.1)
        self.pedestrian_mult.setValue(event_data.get('pedestrian_multiplier', 1.0) if event_data else 1.0)
        self.pedestrian_mult.setDecimals(1)
        layout.addRow("Pedestrian Multiplier:", self.pedestrian_mult)
        
        # Help text
        help_label = QLabel("Multipliers: 1.0 = normal, >1.0 = more traffic, <1.0 = less traffic")
        help_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addRow("", help_label)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        # Initial state
        self.toggle_end_date(self.single_day_check.isChecked())
        
    def toggle_end_date(self, is_single_day):
        """Enable/disable end date based on single day checkbox"""
        self.end_date_edit.setEnabled(not is_single_day)
        if is_single_day:
            self.end_date_edit.setDate(self.start_date_edit.date())
        
    def get_data(self):
        start_date = self.start_date_edit.date()
        end_date = self.end_date_edit.date()
        time_start = self.time_start_edit.time()
        time_end = self.time_end_edit.time()
        
        data = {
            'name': self.event_name_input.text(),
            'start_date': datetime.date(start_date.year(), start_date.month(), start_date.day()).strftime('%Y-%m-%d'),
            'end_date': datetime.date(end_date.year(), end_date.month(), end_date.day()).strftime('%Y-%m-%d'),
            'is_single_day': self.single_day_check.isChecked(),
            'traffic_multiplier': self.traffic_mult.value(),
            'pedestrian_multiplier': self.pedestrian_mult.value()
        }
        
        # Add time range if not default (00:00-23:59)
        if time_start.hour() != 0 or time_start.minute() != 0 or time_end.hour() != 23 or time_end.minute() != 59:
            data['time_start'] = f"{time_start.hour():02d}:{time_start.minute():02d}"
            data['time_end'] = f"{time_end.hour():02d}:{time_end.minute():02d}"
        
        # Add location if provided
        location = self.location_input.text().strip()
        if location:
            data['location'] = location
            
        return data


from PyQt6.QtWidgets import QLineEdit

class EventsManagerDialog(QDialog):
    """Dialog for managing special events"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Special Events")
        self.resize(700, 500)
        
        self.events_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'special_events.json')
        self.events = self._load_events()
        
        self.init_ui()
        self.load_events_to_table()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # City selector
        city_layout = QHBoxLayout()
        city_layout.addWidget(QLabel("City:"))
        self.city_combo = QComboBox()
        self.city_combo.addItems(sorted(self.events.keys()))
        self.city_combo.currentTextChanged.connect(self.load_events_to_table)
        city_layout.addWidget(self.city_combo)
        
        add_city_btn = QPushButton("Add City")
        add_city_btn.clicked.connect(self.add_city)
        city_layout.addWidget(add_city_btn)
        city_layout.addStretch()
        
        layout.addLayout(city_layout)
        
        # Events table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Date Range", "Event Name", "Location", "Traffic Mult", "Ped Mult"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Event")
        add_btn.clicked.connect(self.add_event)
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit Event")
        edit_btn.clicked.connect(self.edit_event)
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("Delete Event")
        delete_btn.clicked.connect(self.delete_event)
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        
        save_btn = QPushButton("Save & Close")
        save_btn.clicked.connect(self.save_and_close)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
    def _load_events(self):
        if not os.path.exists(self.events_path):
            return {}
        try:
            with open(self.events_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
            
    def _save_events(self):
        try:
            with open(self.events_path, 'w', encoding='utf-8') as f:
                json.dump(self.events, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save events: {e}")
            return False
            
    def load_events_to_table(self):
        city = self.city_combo.currentText()
        self.table.setRowCount(0)
        
        if not city or city not in self.events:
            return
            
        city_events = self.events[city]
        for event_key, event_data in sorted(city_events.items()):
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Display date range
            if 'start_date' in event_data:
                if event_data.get('is_single_day', True):
                    date_display = event_data['start_date']
                else:
                    date_display = f"{event_data['start_date']} - {event_data['end_date']}"
            else:
                # Legacy format
                date_display = event_key
            
            self.table.setItem(row, 0, QTableWidgetItem(date_display))
            self.table.setItem(row, 1, QTableWidgetItem(event_data.get('name', '')))
            self.table.setItem(row, 2, QTableWidgetItem(event_data.get('location', '-')))
            self.table.setItem(row, 3, QTableWidgetItem(str(event_data.get('traffic_multiplier', 1.0))))
            self.table.setItem(row, 4, QTableWidgetItem(str(event_data.get('pedestrian_multiplier', 1.0))))
            
    def add_city(self):
        city_name, ok = QInputDialog.getText(self, "Add City", "Enter city name:")
        if ok and city_name:
            if city_name not in self.events:
                self.events[city_name] = {}
                self.city_combo.addItem(city_name)
                self.city_combo.setCurrentText(city_name)
            else:
                QMessageBox.warning(self, "City Exists", f"City '{city_name}' already exists.")
                
    def add_event(self):
        city = self.city_combo.currentText()
        if not city:
            QMessageBox.warning(self, "No City", "Please select or add a city first.")
            return
            
        dialog = EventEditorDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            
            # Use start_date as key for new events
            event_key = data['start_date']
            
            if city not in self.events:
                self.events[city] = {}
                
            self.events[city][event_key] = data
            
            self.load_events_to_table()
            
    def edit_event(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an event to edit.")
            return
            
        city = self.city_combo.currentText()
        
        # Find the event key for this row
        event_key = None
        current_row = 0
        for key in sorted(self.events[city].keys()):
            if current_row == row:
                event_key = key
                break
            current_row += 1
        
        if not event_key:
            return
            
        event_data = self.events[city][event_key]
        
        dialog = EventEditorDialog(self, city, event_key, event_data)
        if dialog.exec():
            data = dialog.get_data()
            new_key = data['start_date']
            
            # Remove old entry if key changed
            if new_key != event_key:
                del self.events[city][event_key]
                
            self.events[city][new_key] = data
            
            self.load_events_to_table()
            
    def delete_event(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an event to delete.")
            return
            
        city = self.city_combo.currentText()
        
        # Find the event key for this row
        event_key = None
        current_row = 0
        for key in sorted(self.events[city].keys()):
            if current_row == row:
                event_key = key
                break
            current_row += 1
        
        if not event_key:
            return
        
        event_name = self.events[city][event_key].get('name', 'this event')
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete '{event_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.events[city][event_key]
            self.load_events_to_table()
            
    def save_and_close(self):
        if self._save_events():
            self.accept()
