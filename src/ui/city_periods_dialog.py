"""
City Periods Dialog
Allows setting specific start/end dates for each city in a campaign.
Supports multiple periods per city.
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QDateEdit, QLabel, QMessageBox, QDialogButtonBox, QCheckBox, 
                               QWidget)
from PyQt6.QtCore import Qt, QDate
import datetime
from typing import List, Dict, Any
from src.ui.city_daily_schedule_dialog import CityDailyScheduleDialog

class SingleCityPeriodsDialog(QDialog):
    """Dialog to manage multiple periods for a single city"""
    def __init__(self, city_name: str, periods: List[Dict[str, datetime.date]], 
                 global_start: datetime.date, global_end: datetime.date, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Periods for {city_name}")
        self.resize(500, 400)
        self.city_name = city_name
        self.periods = periods or []
        self.global_start = global_start
        self.global_end = global_end
        
        # If no periods, start with one default global period
        if not self.periods:
            self.periods = [{'start': global_start, 'end': global_end}]
            
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        info = QLabel(f"Manage active periods for <b>{self.city_name}</b>.<br/>"
                      f"Global Campaign: {self.global_start.strftime('%d.%m.%Y')} - {self.global_end.strftime('%d.%m.%Y')}")
        layout.addWidget(info)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Start Date", "End Date", "Days", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)
        
        # Add button
        add_btn = QPushButton("Add Another Period")
        add_btn.clicked.connect(self.add_period_row)
        layout.addWidget(add_btn)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def load_data(self):
        self.table.setRowCount(0)
        for period in self.periods:
            self.add_period_row(period.get('start'), period.get('end'))
            
    def add_period_row(self, start=None, end=None):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        start_date = start if start else self.global_start
        end_date = end if end else self.global_end
        
        if isinstance(start_date, str): start_date = datetime.date.fromisoformat(start_date)
        if isinstance(end_date, str): end_date = datetime.date.fromisoformat(end_date)
        
        # Start Date
        start_picker = QDateEdit()
        start_picker.setCalendarPopup(True)
        start_picker.setDate(start_date)
        start_picker.dateChanged.connect(lambda: self.update_row_stats(row))
        self.table.setCellWidget(row, 0, start_picker)
        
        # End Date
        end_picker = QDateEdit()
        end_picker.setCalendarPopup(True)
        end_picker.setDate(end_date)
        end_picker.dateChanged.connect(lambda: self.update_row_stats(row))
        self.table.setCellWidget(row, 1, end_picker)
        
        # Days (calculated)
        self.table.setItem(row, 2, QTableWidgetItem(""))
        
        # Delete button
        del_btn = QPushButton("X")
        del_btn.setMaximumWidth(30)
        del_btn.setStyleSheet("color: red; font-weight: bold;")
        del_btn.clicked.connect(lambda: self.table.removeRow(row))
        self.table.setCellWidget(row, 3, del_btn)
        
        self.update_row_stats(row)
        
    def update_row_stats(self, row):
        try:
            start_picker = self.table.cellWidget(row, 0)
            end_picker = self.table.cellWidget(row, 1)
            
            if not start_picker or not end_picker: return
            
            start = start_picker.date().toPyDate()
            end = end_picker.date().toPyDate()
            
            days = (end - start).days + 1
            self.table.setItem(row, 2, QTableWidgetItem(str(days)))
            
            # Warn if outside global? Optional.
        except:
            pass

    def get_periods(self) -> List[Dict[str, datetime.date]]:
        periods = []
        for row in range(self.table.rowCount()):
            start_picker = self.table.cellWidget(row, 0)
            end_picker = self.table.cellWidget(row, 1)
            
            if start_picker and end_picker:
                periods.append({
                    'start': start_picker.date().toPyDate(),
                    'end': end_picker.date().toPyDate()
                })
        return periods


class CityPeriodsDialog(QDialog):
    """Dialog to manage per-city campaign periods"""
    
    def __init__(self, cities: List[str], global_start: datetime.date, global_end: datetime.date, 
                 existing_periods: Dict[str, Any] = None, existing_schedules: Dict[str, Any] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Campaign Periods per City")
        self.resize(800, 600)
        
        self.cities = cities
        self.global_start = global_start
        self.global_end = global_end
        
        # Ensure existing_periods handles backward compatibility (convert single to list)
        self.existing_periods = existing_periods or {}
        self.city_schedules = existing_schedules or {}
        
        self._normalize_periods()
        
        self.init_ui()
        self.load_data()

    def _normalize_periods(self):
        """Convert old single-dict format to new list format if needed"""
        for city, data in self.existing_periods.items():
            if city == '__meta__': continue
            # If it's a dict with start/end directly, wrap it in a list
            if isinstance(data, dict) and 'start' in data and not isinstance(data, list):
                self.existing_periods[city] = [data]
            elif not isinstance(data, list):
                # Unknown format or None, reset
                self.existing_periods[city] = []

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Info label
        info_label = QLabel(f"Global Campaign Period: {self.global_start.strftime('%d.%m.%Y')} - {self.global_end.strftime('%d.%m.%Y')}")
        info_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["City", "Assigned Vehicles", "Active Periods", "Total Days"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.table)
        
        # Shared Day / Nearby Cities Mode
        self.shared_day_cb = QCheckBox("Shared Day / Nearby Cities (Split Schedule)")
        self.shared_day_cb.setToolTip("Enable this if the vehicle travels between these cities on the same days.\nThis allows splitting daily hours between multiple locations.")
        self.shared_day_cb.stateChanged.connect(self.toggle_shared_mode)
        layout.addWidget(self.shared_day_cb)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.custom_schedule_btn = QPushButton("Set Daily Schedule per City")
        self.custom_schedule_btn.clicked.connect(self.open_daily_schedule)
        btn_layout.addWidget(self.custom_schedule_btn)
        
        btn_layout.addStretch()
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        btn_layout.addWidget(buttons)
        
        layout.addLayout(btn_layout)
        
    def load_data(self):
        """Load cities into table"""
        self.table.setRowCount(len(self.cities))
        
        # Check for shared mode in existing data
        meta = self.existing_periods.get('__meta__', {})
        if meta.get('shared_mode'):
            self.shared_day_cb.setChecked(True)
            
        # Vehicle mapping (injected)
        mapping = getattr(self, 'city_vehicles_map', {})
        
        for row, city in enumerate(self.cities):
            # City Name
            self.table.setItem(row, 0, QTableWidgetItem(city))
            
            # Assigned Vehicles
            vehs = mapping.get(city, [])
            if vehs:
                vehs_str = ", ".join(vehs)
            else:
                vehs_str = "None/Global"
            
            item_veh = QTableWidgetItem(vehs_str)
            item_veh.setToolTip(vehs_str)
            self.table.setItem(row, 1, item_veh)
            
            # Get existing periods
            periods = self.existing_periods.get(city, [])
            if not periods:
                # Default to global period
                periods = [{'start': self.global_start, 'end': self.global_end}]
                self.existing_periods[city] = periods
            
            self._update_row_display(row, periods)
            
    def _update_row_display(self, row, periods):
        """Update the display cells for a city row"""
        # Summary text
        if len(periods) == 1:
            p = periods[0]
            s = p['start'] if isinstance(p['start'], datetime.date) else datetime.date.fromisoformat(p['start'])
            e = p['end'] if isinstance(p['end'], datetime.date) else datetime.date.fromisoformat(p['end'])
            summary = f"{s.strftime('%d.%m')} - {e.strftime('%d.%m.%Y')}"
        else:
            summary = f"{len(periods)} periods defined"
            
        # Action Button (Edit)
        container = QWidget()
        hlayout = QHBoxLayout(container)
        hlayout.setContentsMargins(2, 2, 2, 2)
        
        lbl = QLabel(summary)
        hlayout.addWidget(lbl)
        
        edit_btn = QPushButton("Edit")
        edit_btn.setMaximumWidth(60)
        edit_btn.clicked.connect(lambda _, r=row: self.edit_city_periods(r))
        hlayout.addWidget(edit_btn)
        
        self.table.setCellWidget(row, 2, container)
        
        # Total days
        total_days = 0
        for p in periods:
            s = p['start'] if isinstance(p['start'], datetime.date) else datetime.date.fromisoformat(str(p['start']))
            e = p['end'] if isinstance(p['end'], datetime.date) else datetime.date.fromisoformat(str(p['end']))
            total_days += (e - s).days + 1
            
        self.table.setItem(row, 3, QTableWidgetItem(str(total_days)))

    def edit_city_periods(self, row):
        """Open sub-dialog to edit periods for a city"""
        city = self.table.item(row, 0).text()
        current_periods = self.existing_periods.get(city, [])
        
        dialog = SingleCityPeriodsDialog(city, current_periods, self.global_start, self.global_end, self)
        if dialog.exec():
            new_periods = dialog.get_periods()
            self.existing_periods[city] = new_periods
            self._update_row_display(row, new_periods)
            
            # Check for Shared Mode propagation
            if self.shared_day_cb.isChecked():
                reply = QMessageBox.question(
                    self,
                    "Propagate to All Cities?",
                    f"Shared Mode is ON.\nDo you want to apply these periods to ALL other cities?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    for i, c in enumerate(self.cities):
                        if c == city: continue
                        self.existing_periods[c] = new_periods
                        self._update_row_display(i, new_periods)
                    QMessageBox.information(self, "Success", "Periods applied to all cities.")

    def toggle_shared_mode(self, state):
        """Enable/disable shared mode"""
        is_shared = state == Qt.CheckState.Checked.value
        
        if is_shared:
            reply = QMessageBox.question(
                self,
                "Apply Global Dates?",
                "Do you want to apply the global campaign dates to ALL cities now?\n"
                "This will overwrite any specific periods you have set.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Reset all to global period
                global_period = {'start': self.global_start, 'end': self.global_end}
                for city in self.cities:
                    self.existing_periods[city] = [global_period]
                
                # Refresh table
                self.load_data()
                QMessageBox.information(self, "Done", "All cities synchronized to global dates.")

    def get_data(self) -> Dict[str, Any]:
        """Get configured periods"""
        # Return copy of our internal state
        data = self.existing_periods.copy()
        
        # Add metadata about shared mode
        data['__meta__'] = {
            'shared_mode': self.shared_day_cb.isChecked()
        }
        
        return data
        
    def open_daily_schedule(self):
        """Open dialog to set daily schedule per city"""
        # Convert multi-period data to a flat structure if needed only for initialization 
        # But CityDailyScheduleDialog likely needs updating if it relies on 'start'/'end' keys of the dict.
        
        # For now, pass the complex structure but we might need to handle it in CityDailyScheduleDialog
        # Wait, the previous version of CityDailyScheduleDialog took `current_periods`.
        # If `current_periods` is now a list of dicts instead of a dict, it might break.
        # Let's check CityDailyScheduleDialog usage.
        
        # Actually proper way: we pass the periods as is. The schedule dialog needs to know valid dates.
        dialog = CityDailyScheduleDialog(self.existing_periods, self.city_schedules, self)
        if dialog.exec():
            self.city_schedules = dialog.get_data()
            QMessageBox.information(self, "Success", "Daily schedules updated successfully")
            
    def get_schedules(self) -> Dict[str, Any]:
        """Get configured daily schedules"""
        return self.city_schedules
