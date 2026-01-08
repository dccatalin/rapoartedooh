"""
City Daily Schedule Dialog
Allows setting specific hours for each day in each city.
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QTimeEdit, QLabel, QMessageBox, QDialogButtonBox,
                               QTabWidget, QWidget, QCheckBox, QInputDialog)
from PyQt6.QtCore import Qt, QTime, QDate
import datetime
from typing import List, Dict, Any

class CityDailyScheduleDialog(QDialog):
    """Dialog to manage daily schedules per city"""
    
    def __init__(self, city_periods: Dict[str, List[Dict[str, datetime.date]]], 
                 existing_schedules: Dict[str, Any] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Daily Schedule per City")
        self.resize(800, 600)
        
        self.city_periods = city_periods
        self.existing_schedules = existing_schedules or {}
        self.tables = {} # Store tables for each city
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Tabs for each city
        self.tabs = QTabWidget()
        
        for city, periods in self.city_periods.items():
            if city == '__meta__': continue
            # Handle backward compatibility if it's still a single dict
            if isinstance(periods, dict):
                periods = [periods]
                
            tab = self.create_city_tab(city, periods)
            self.tabs.addTab(tab, city)
            
        layout.addWidget(self.tabs)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def create_city_tab(self, city: str, periods: List[Dict[str, datetime.date]]) -> QWidget:
        """Create tab for a specific city"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Toolbar
        toolbar = QHBoxLayout()
        copy_btn = QPushButton("Copy First Day to All")
        copy_btn.clicked.connect(lambda: self.copy_to_all(city))
        toolbar.addWidget(copy_btn)
        
        set_hours_btn = QPushButton("Set Hours Range")
        set_hours_btn.clicked.connect(lambda: self.set_hours_range(city))
        toolbar.addWidget(set_hours_btn)
        
        # Check for shared mode
        meta = self.city_periods.get('__meta__', {})
        if meta.get('shared_mode'):
            split_btn = QPushButton("Split Hours (Shared Day)")
            split_btn.setToolTip("Helper to split hours between cities for this day")
            split_btn.clicked.connect(lambda: self.split_hours_helper(city))
            toolbar.addWidget(split_btn)
        
        layout.addLayout(toolbar)
        
        # Table
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Date", "Start Time", "End Time", "Active"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        # Populate dates from all periods
        row = 0
        city_schedule = self.existing_schedules.get(city, {})
        
        # Sort periods by start date just in case
        sorted_periods = sorted(periods, key=lambda x: x.get('start', datetime.date.min))
        
        for period in sorted_periods:
            p_start = period.get('start')
            p_end = period.get('end')
            
            if isinstance(p_start, str): p_start = datetime.date.fromisoformat(p_start)
            if isinstance(p_end, str): p_end = datetime.date.fromisoformat(p_end)
            
            current_date = p_start
            while current_date <= p_end:
                table.insertRow(row)
                
                # Date
                date_str = current_date.strftime('%Y-%m-%d')
                table.setItem(row, 0, QTableWidgetItem(current_date.strftime('%d.%m.%Y (%A)')))
                table.item(row, 0).setData(Qt.ItemDataRole.UserRole, date_str)
                
                # Get existing data for this date
                day_data = city_schedule.get(date_str, {})
                hours = day_data.get('hours', '09:00-17:00')
                active = day_data.get('active', True)
                
                try:
                    start_str, end_str = hours.split('-')
                    start_h, start_m = map(int, start_str.split(':'))
                    end_h, end_m = map(int, end_str.split(':'))
                except:
                    start_h, start_m = 9, 0
                    end_h, end_m = 17, 0
                
                # Start Time
                start_edit = QTimeEdit()
                start_edit.setTime(QTime(start_h, start_m))
                table.setCellWidget(row, 1, start_edit)
                
                # End Time
                end_edit = QTimeEdit()
                end_edit.setTime(QTime(end_h, end_m))
                table.setCellWidget(row, 2, end_edit)
                
                # Active
                active_cb = QCheckBox()
                active_cb.setChecked(active)
                # Center checkbox
                cb_widget = QWidget()
                cb_layout = QHBoxLayout(cb_widget)
                cb_layout.addWidget(active_cb)
                cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cb_layout.setContentsMargins(0, 0, 0, 0)
                table.setCellWidget(row, 3, cb_widget)
                
                current_date += datetime.timedelta(days=1)
                row += 1
            
        layout.addWidget(table)
        self.tables[city] = table
        
        return tab
        
    def copy_to_all(self, city: str):
        """Copy settings from first row to all rows for a city"""
        table = self.tables[city]
        if table.rowCount() == 0:
            return
            
        start_time = table.cellWidget(0, 1).time()
        end_time = table.cellWidget(0, 2).time()
        
        # Get checkbox state from first row
        first_cb_widget = table.cellWidget(0, 3)
        first_cb = first_cb_widget.findChild(QCheckBox)
        active = first_cb.isChecked()
        
        for row in range(1, table.rowCount()):
            table.cellWidget(row, 1).setTime(start_time)
            table.cellWidget(row, 2).setTime(end_time)
            
            cb_widget = table.cellWidget(row, 3)
            cb = cb_widget.findChild(QCheckBox)
            cb.setChecked(active)
            
    def set_hours_range(self, city: str):
        """Set specific hours range for all days"""
        start_str, ok1 = QInputDialog.getText(self, "Start Time", "Start Time (HH:MM):", text="09:00")
        if not ok1: return
        
        end_str, ok2 = QInputDialog.getText(self, "End Time", "End Time (HH:MM):", text="17:00")
        if not ok2: return
        
        try:
            start_h, start_m = map(int, start_str.split(':'))
            end_h, end_m = map(int, end_str.split(':'))
            start_time = QTime(start_h, start_m)
            end_time = QTime(end_h, end_m)
            
            table = self.tables[city]
            for row in range(table.rowCount()):
                table.cellWidget(row, 1).setTime(start_time)
                table.cellWidget(row, 2).setTime(end_time)
        except:
            QMessageBox.warning(self, "Error", "Invalid time format. Use HH:MM")

    def split_hours_helper(self, current_city: str):
        """Helper to split hours between cities"""
        # Get all cities involved
        cities = [c for c in self.city_periods.keys() if c != '__meta__']
        count = len(cities)
        
        if count < 2:
            QMessageBox.information(self, "Info", "Need at least 2 cities to split hours.")
            return
            
        # Simple split logic: Divide 09:00-17:00 (8 hours) by number of cities
        total_hours = 8
        hours_per_city = total_hours / count
        
        start_h = 9
        
        msg = "Proposed Split:\n\n"
        
        splits = {}
        
        for i, city in enumerate(cities):
            end_h = start_h + hours_per_city
            
            # Format
            s_h = int(start_h)
            s_m = int((start_h - s_h) * 60)
            e_h = int(end_h)
            e_m = int((end_h - e_h) * 60)
            
            splits[city] = (QTime(s_h, s_m), QTime(e_h, e_m))
            
            msg += f"{city}: {s_h:02d}:{s_m:02d} - {e_h:02d}:{e_m:02d}\n"
            
            start_h = end_h
            
        msg += "\nApply this split to ALL days?"
        
        reply = QMessageBox.question(self, "Split Hours", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            for city, (start, end) in splits.items():
                if city in self.tables:
                    table = self.tables[city]
                    for row in range(table.rowCount()):
                        table.cellWidget(row, 1).setTime(start)
                        table.cellWidget(row, 2).setTime(end)
            
            QMessageBox.information(self, "Success", "Hours split applied to all cities!")

    def get_data(self) -> Dict[str, Dict[str, Any]]:
        """Get configured schedules"""
        schedules = {}
        
        for city, table in self.tables.items():
            city_schedule = {}
            for row in range(table.rowCount()):
                date_str = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                start_time = table.cellWidget(row, 1).time().toString("HH:mm")
                end_time = table.cellWidget(row, 2).time().toString("HH:mm")
                
                cb_widget = table.cellWidget(row, 3)
                cb = cb_widget.findChild(QCheckBox)
                active = cb.isChecked()
                
                city_schedule[date_str] = {
                    'hours': f"{start_time}-{end_time}",
                    'active': active
                }
            schedules[city] = city_schedule
            
        return schedules
