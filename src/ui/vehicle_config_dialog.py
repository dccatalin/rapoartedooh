from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QComboBox, 
                               QLabel, QDialogButtonBox, QMessageBox, QCheckBox,
                               QGroupBox, QListWidget, QAbstractItemView, QHBoxLayout,
                               QTableWidget, QHeaderView, QPushButton, QTableWidgetItem)
from PyQt6.QtCore import Qt, QDate
from src.data.vehicle_manager import VehicleManager
from src.data.city_data_manager import CityDataManager

class VehicleConfigDialog(QDialog):
    def __init__(self, parent=None, vehicle_data=None, available_cities=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Vehicle")
        self.resize(400, 500)
        
        self.vehicle_manager = VehicleManager()
        self.city_manager = CityDataManager()
        self.vehicle_data = vehicle_data or {}
        self.available_cities = available_cities or [] # Cities selected in main campaign
        
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # Vehicle
        self.vehicle_combo = QComboBox()
        self.vehicle_combo.addItem("Select Vehicle...", None)
        vehicles = self.vehicle_manager.get_active_vehicles()
        for v in vehicles:
            self.vehicle_combo.addItem(f"{v['name']} ({v.get('registration', '')})", v['id'])
        self.vehicle_combo.currentIndexChanged.connect(self.update_driver)
        form_layout.addRow("Vehicle:", self.vehicle_combo)
        
        # Driver
        self.driver_combo = QComboBox()
        self.driver_combo.addItem("Select Driver...", None)
        form_layout.addRow("Driver:", self.driver_combo)
        
        layout.addLayout(form_layout)
        
        # City Override
        self.check_city_override = QCheckBox("Override Campaign Cities")
        self.check_city_override.setToolTip("Select specific cities for this vehicle only")
        self.check_city_override.toggled.connect(self.toggle_city_list)
        layout.addWidget(self.check_city_override)
        
        self.city_group = QGroupBox("Specific Cities")
        city_layout = QVBoxLayout()
        self.city_list = QListWidget()
        self.city_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        # Load all cities
        all_cities = self.city_manager.get_all_cities()
        self.city_list.addItems(all_cities)
        city_layout.addWidget(self.city_list)
        self.city_group.setLayout(city_layout)
        self.city_group.setVisible(False)
        layout.addWidget(self.city_group)

        # Transit Periods
        self.transit_group = QGroupBox("Transit / Unavailable Periods")
        transit_layout = QVBoxLayout()
        
        # Table
        self.transit_table = QTableWidget()
        self.transit_table.setColumnCount(4)
        self.transit_table.setHorizontalHeaderLabels(["Start", "End", "From", "To"])
        self.transit_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.transit_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.transit_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.transit_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.transit_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.transit_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.transit_table.setFixedHeight(120)
        
        transit_layout.addWidget(self.transit_table)
        
        # Buttons
        t_btn_layout = QHBoxLayout()
        add_transit_btn = QPushButton("Add Period")
        add_transit_btn.clicked.connect(self.add_transit)
        t_btn_layout.addWidget(add_transit_btn)
        
        rem_transit_btn = QPushButton("Remove Period")
        rem_transit_btn.clicked.connect(self.remove_transit)
        t_btn_layout.addWidget(rem_transit_btn)
        
        t_btn_layout.addStretch()
        transit_layout.addLayout(t_btn_layout)
        
        self.transit_group.setLayout(transit_layout)
        layout.addWidget(self.transit_group)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def toggle_city_list(self, checked):
        self.city_group.setVisible(checked)
        
    def update_driver(self):
        vehicle_id = self.vehicle_combo.currentData()
        self.driver_combo.clear()
        
        if vehicle_id:
            vehicle = self.vehicle_manager.get_vehicle(vehicle_id)
            if vehicle:
                # Pre-select assigned driver
                d_id = vehicle.get('driver_id')
                d_name = vehicle.get('driver_name') or "Unknown"
                if d_id:
                    self.driver_combo.addItem(d_name, d_id)
                else:
                    self.driver_combo.addItem("No Driver Assigned", None)
                    # Maybe load all drivers if needed? For now stick to vehicle's driver or manual override logic if we had list
        else:
            self.driver_combo.addItem("Select Driver...", None)
            
    def load_data(self):
        if not self.vehicle_data:
            return
            
        # Set vehicle
        v_id = self.vehicle_data.get('vehicle_id')
        if v_id:
            idx = self.vehicle_combo.findData(v_id)
            if idx >= 0:
                self.vehicle_combo.setCurrentIndex(idx)
                
        # Set specific cities
        specific_cities = self.vehicle_data.get('cities', [])
        if specific_cities:
            self.check_city_override.setChecked(True)
            for i in range(self.city_list.count()):
                item = self.city_list.item(i)
                if item.text() in specific_cities:
                    item.setSelected(True)
                    
        # Load Transit Periods
        transits = self.vehicle_data.get('transit_periods', [])
        for t in transits:
            self._add_transit_row(t.get('start'), t.get('end'), t.get('from'), t.get('to'))
                    
    def validate_and_accept(self):
        if not self.vehicle_combo.currentData():
            QMessageBox.warning(self, "Error", "Please select a vehicle.")
            return
            
        self.accept()
        
    def get_vehicle_config(self):
        v_id = self.vehicle_combo.currentData()
        v_name = self.vehicle_combo.currentText()
        d_id = self.driver_combo.currentData()
        d_name = self.driver_combo.currentText()
        
        cities = []
        if self.check_city_override.isChecked():
            for item in self.city_list.selectedItems():
                cities.append(item.text())
        
        # Collect Transit
        transits = []
        for row in range(self.transit_table.rowCount()):
            transits.append({
                'start': self.transit_table.item(row, 0).text(),
                'end': self.transit_table.item(row, 1).text(),
                'from': self.transit_table.item(row, 2).text(),
                'to': self.transit_table.item(row, 3).text()
            })
        
        return {
            'vehicle_id': v_id,
            'vehicle_name': v_name.split(' (')[0], # Clean name
            'driver_id': d_id,
            'driver_name': d_name,
            'cities': cities, # Empty means use global
            'override_cities': self.check_city_override.isChecked(),
            'transit_periods': transits
        }
        
    def add_transit(self):
        """Show small dialog to add transit period"""
        # We can reuse VehicleEventDialog or create a simpler inline one
        # Let's create a quick dialog here
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Transit Period")
        layout = QVBoxLayout(dialog)
        
        from PyQt6.QtWidgets import QDateEdit
        
        form = QFormLayout()
        
        start_edit = QDateEdit()
        start_edit.setCalendarPopup(True)
        start_edit.setDate(QDate.currentDate())
        form.addRow("Start Date:", start_edit)
        
        end_edit = QDateEdit()
        end_edit.setCalendarPopup(True)
        end_edit.setDate(QDate.currentDate())
        form.addRow("End Date:", end_edit)
        
        # Cities
        all_cities = sorted(self.city_manager.get_all_cities())
        
        from_combo = QComboBox()
        from_combo.setEditable(True)
        from_combo.addItems(all_cities)
        form.addRow("From City:", from_combo)
        
        to_combo = QComboBox()
        to_combo.setEditable(True)
        to_combo.addItems(all_cities)
        form.addRow("To City:", to_combo)
        
        layout.addLayout(form)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addWidget(btns)
        
        if dialog.exec():
            s = start_edit.date().toString("yyyy-MM-dd")
            e = end_edit.date().toString("yyyy-MM-dd")
            f = from_combo.currentText()
            t = to_combo.currentText()
            
            self._add_transit_row(s, e, f, t)
            
    def _add_transit_row(self, start, end, origin, dest):
        from PyQt6.QtWidgets import QTableWidgetItem
        row = self.transit_table.rowCount()
        self.transit_table.insertRow(row)
        self.transit_table.setItem(row, 0, QTableWidgetItem(start))
        self.transit_table.setItem(row, 1, QTableWidgetItem(end))
        self.transit_table.setItem(row, 2, QTableWidgetItem(origin))
        self.transit_table.setItem(row, 3, QTableWidgetItem(dest))
        
    def remove_transit(self):
        row = self.transit_table.currentRow()
        if row >= 0:
            self.transit_table.removeRow(row)
