"""
Fleet Management Dialog
Manages vehicles and drivers with two-tab interface.
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTableWidget, QTableWidgetItem, QTabWidget,
                               QWidget, QMessageBox, QInputDialog, QComboBox,
                               QLabel, QFormLayout, QLineEdit, QDialogButtonBox,
                               QHeaderView)
from PyQt6.QtCore import Qt
from src.data.driver_manager import DriverManager
from src.data.vehicle_manager import VehicleManager
import logging

logger = logging.getLogger(__name__)


class FleetManagementDialog(QDialog):
    """Dialog for managing fleet (vehicles and drivers)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fleet Management")
        self.resize(900, 600)
        
        self.driver_manager = DriverManager()
        self.vehicle_manager = VehicleManager()
        
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # Vehicles tab
        vehicles_tab = self.create_vehicles_tab()
        self.tabs.addTab(vehicles_tab, "Vehicles")
        
        # Drivers tab
        drivers_tab = self.create_drivers_tab()
        self.tabs.addTab(drivers_tab, "Drivers")
        
        layout.addWidget(self.tabs)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def create_vehicles_tab(self) -> QWidget:
        """Create vehicles management tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        add_btn = QPushButton("Add Vehicle")
        add_btn.clicked.connect(self.add_vehicle)
        toolbar.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit Vehicle")
        edit_btn.clicked.connect(self.edit_vehicle)
        toolbar.addWidget(edit_btn)
        
        delete_btn = QPushButton("Delete Vehicle")
        delete_btn.clicked.connect(self.delete_vehicle)
        toolbar.addWidget(delete_btn)
        
        toolbar.addStretch()
        
        assign_driver_btn = QPushButton("Manage Driver")
        assign_driver_btn.clicked.connect(self.manage_vehicle_driver)
        toolbar.addWidget(assign_driver_btn)
        
        status_btn = QPushButton("Change Status")
        status_btn.clicked.connect(self.change_vehicle_status)
        toolbar.addWidget(status_btn)
        
        layout.addLayout(toolbar)
        
        # Secondary Toolbar
        toolbar2 = QHBoxLayout()
        
        add_event_btn = QPushButton("Add Event")
        add_event_btn.clicked.connect(self.add_vehicle_event)
        toolbar2.addWidget(add_event_btn)
        
        history_btn = QPushButton("View History")
        history_btn.clicked.connect(self.view_vehicle_history)
        toolbar2.addWidget(history_btn)
        
        toolbar2.addStretch()
        layout.addLayout(toolbar2)
        
        # Table
        self.vehicles_table = QTableWidget()
        self.vehicles_table.setColumnCount(6)
        self.vehicles_table.setHorizontalHeaderLabels([
            "Name", "Registration", "Driver", "Status", "Created", "ID"
        ])
        self.vehicles_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.vehicles_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.vehicles_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.vehicles_table)
        
        return tab
    
    def create_drivers_tab(self) -> QWidget:
        """Create drivers management tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        add_btn = QPushButton("Add Driver")
        add_btn.clicked.connect(self.add_driver)
        toolbar.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit Driver")
        edit_btn.clicked.connect(self.edit_driver)
        toolbar.addWidget(edit_btn)
        
        delete_btn = QPushButton("Delete Driver")
        delete_btn.clicked.connect(self.delete_driver)
        toolbar.addWidget(delete_btn)
        
        toolbar.addStretch()
        
        manage_btn = QPushButton("Manage Vehicle")
        manage_btn.clicked.connect(self.manage_driver_assignment)
        toolbar.addWidget(manage_btn)
        
        add_event_btn = QPushButton("Add Event")
        add_event_btn.clicked.connect(self.add_driver_event)
        toolbar.addWidget(add_event_btn)
        
        history_btn = QPushButton("View History")
        history_btn.clicked.connect(self.view_driver_history)
        toolbar.addWidget(history_btn)
        
        layout.addLayout(toolbar)
        
        # Table
        self.drivers_table = QTableWidget()
        self.drivers_table.setColumnCount(6)
        self.drivers_table.setHorizontalHeaderLabels([
            "Name", "Phone", "License", "Assigned Vehicle", "Status", "ID"
        ])
        self.drivers_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.drivers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.drivers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.drivers_table)
        
        return tab
    
    def load_data(self):
        """Load vehicles and drivers into tables"""
        self.load_vehicles()
        self.load_drivers()
    
    def load_vehicles(self):
        """Load vehicles into table"""
        vehicles = self.vehicle_manager.get_all_vehicles()
        self.vehicles_table.setRowCount(len(vehicles))
        
        for row, vehicle in enumerate(vehicles):
            self.vehicles_table.setItem(row, 0, QTableWidgetItem(vehicle.get('name', '')))
            self.vehicles_table.setItem(row, 1, QTableWidgetItem(vehicle.get('registration', '')))
            self.vehicles_table.setItem(row, 2, QTableWidgetItem(vehicle.get('driver_name', 'No driver')))
            
            # Color-code status
            # Check documents for expiry
            expired_docs = []
            from datetime import date
            today = date.today()
            
            for doc_field in ['rca_expiry', 'itp_expiry', 'rovinieta_expiry', 'casco_expiry']:
                expiry_str = vehicle.get(doc_field)
                if expiry_str:
                    # Parse iso string
                    try:
                        exp_date = date.fromisoformat(expiry_str[:10])
                        if exp_date < today:
                             expired_docs.append(doc_field.replace('_expiry', '').upper())
                    except:
                        pass
            
            # Status Item
            status = vehicle.get('status', 'unknown')
            status_disp = status.capitalize()
            if expired_docs:
                status_disp += f" [EXPIRED: {', '.join(expired_docs)}]"
                
            status_item = QTableWidgetItem(status_disp)
            
            if expired_docs:
                status_item.setForeground(Qt.GlobalColor.red)
                f = status_item.font()
                f.setBold(True)
                status_item.setFont(f)
            elif status == 'active':
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            elif status == 'defective':
                status_item.setForeground(Qt.GlobalColor.red)
            elif status == 'maintenance':
                status_item.setForeground(Qt.GlobalColor.darkYellow)
            
            self.vehicles_table.setItem(row, 3, status_item)
            self.vehicles_table.setItem(row, 4, QTableWidgetItem(vehicle.get('created', '')[:10]))
            self.vehicles_table.setItem(row, 5, QTableWidgetItem(vehicle.get('id', '')))
    
    def load_drivers(self):
        """Load drivers into table"""
        drivers = self.driver_manager.get_all_drivers()
        self.drivers_table.setRowCount(len(drivers))
        
        for row, driver in enumerate(drivers):
            self.drivers_table.setItem(row, 0, QTableWidgetItem(driver.get('name', '')))
            self.drivers_table.setItem(row, 1, QTableWidgetItem(driver.get('phone', '')))
            self.drivers_table.setItem(row, 2, QTableWidgetItem(driver.get('license_number', '')))
            
            # Get vehicle name if assigned
            vehicle_name = "Unassigned"
            if driver.get('assigned_vehicle'):
                vehicle = self.vehicle_manager.get_vehicle(driver['assigned_vehicle'])
                if vehicle:
                    vehicle_name = vehicle.get('name', driver['assigned_vehicle'])
            
            self.drivers_table.setItem(row, 3, QTableWidgetItem(vehicle_name))
            
            # Color-code status
            status = driver.get('status', 'unknown')
            status_item = QTableWidgetItem(status.capitalize())
            if status == 'active':
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                status_item.setForeground(Qt.GlobalColor.gray)
            
            self.drivers_table.setItem(row, 4, status_item)
            self.drivers_table.setItem(row, 5, QTableWidgetItem(driver.get('id', '')))
    
    # Vehicle operations
    def add_vehicle(self):
        """Add a new vehicle"""
        dialog = VehicleEditDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            self.vehicle_manager.add_vehicle(
                data['name'],
                data['registration'],
                data['status']
            )
            self.load_vehicles()
            QMessageBox.information(self, "Success", "Vehicle added successfully")
    
    def edit_vehicle(self):
        """Edit selected vehicle"""
        row = self.vehicles_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a vehicle to edit")
            return
        
        vehicle_id = self.vehicles_table.item(row, 5).text()
        vehicle = self.vehicle_manager.get_vehicle(vehicle_id)
        
        if not vehicle:
            QMessageBox.critical(self, "Error", "Vehicle not found")
            return
        
        dialog = VehicleEditDialog(self, vehicle)
        if dialog.exec():
            data = dialog.get_data()
            self.vehicle_manager.update_vehicle(
                vehicle_id,
                data['name'],
                data['registration'],
                data['status']
            )
            self.load_vehicles()
            QMessageBox.information(self, "Success", "Vehicle updated successfully")
    
    def delete_vehicle(self):
        """Delete selected vehicle"""
        row = self.vehicles_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a vehicle to delete")
            return
        
        vehicle_id = self.vehicles_table.item(row, 5).text()
        vehicle_name = self.vehicles_table.item(row, 0).text()
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete vehicle '{vehicle_name}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.vehicle_manager.delete_vehicle(vehicle_id):
                self.load_vehicles()
                QMessageBox.information(self, "Success", "Vehicle deleted successfully")
            else:
                QMessageBox.critical(self, "Error", "Failed to delete vehicle")
    
    def manage_vehicle_driver(self):
        """Manage driver assignment for selected vehicle (Assign/Unassign)"""
        row = self.vehicles_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a vehicle")
            return
        
        vehicle_id = self.vehicles_table.item(row, 5).text()
        vehicle_name = self.vehicles_table.item(row, 0).text()
        current_driver_name = self.vehicles_table.item(row, 2).text()
        
        # Determine current state
        has_driver = current_driver_name != "No driver"
        
        # Get all active drivers
        all_drivers = self.driver_manager.get_active_drivers()
        if not all_drivers:
            QMessageBox.warning(self, "No Drivers", "No active drivers available")
            return
            
        # Prepare list for dialog
        # Format: "Name (Phone) [Assigned to: X]"
        driver_options = []
        current_driver_idx = 0
        
        for i, d in enumerate(all_drivers):
            assigned_to = ""
            if d.get('assigned_vehicle'):
                v_name = "Another Vehicle"
                # If assigned to THIS vehicle
                if d['assigned_vehicle'] == vehicle_id:
                    v_name = "THIS VEHICLE"
                    current_driver_idx = i
                else:
                    # Try to find name of other vehicle
                    v = self.vehicle_manager.get_vehicle(d['assigned_vehicle'])
                    if v: v_name = v.get('name', 'Unknown')
                assigned_to = f" [Assigned to: {v_name}]"
            
            driver_options.append(f"{d['name']} ({d.get('phone', '-')}){assigned_to}")
            
        # UI Dialog
        # We need a custom dialog to allow "Unassign"
        from PyQt6.QtWidgets import QVBoxLayout, QLabel, QComboBox, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Manage Driver for '{vehicle_name}'")
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel(f"Current Driver: {current_driver_name}"))
        layout.addWidget(QLabel("Select New Driver:"))
        
        combo = QComboBox()
        combo.addItems(driver_options)
        # Select current if applicable
        if has_driver:
            combo.setCurrentIndex(current_driver_idx)
            
        layout.addWidget(combo)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        
        # Unassign Button
        unassign_btn = None
        if has_driver:
            unassign_btn = btn_box.addButton("Unassign Driver", QDialogButtonBox.ButtonRole.DestructiveRole)
            
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)
        
        # Track unassign action
        dialog.unassign_requested = False
        def on_unassign():
            dialog.unassign_requested = True
            dialog.reject() # Close dialog
            
        if unassign_btn:
            unassign_btn.clicked.connect(on_unassign)
        
        # Execute
        dialog.exec()
        
        if dialog.result() == QDialog.DialogCode.Accepted:
            # OK pressed -> Assign selected
            selected_idx = combo.currentIndex()
            selected_driver = all_drivers[selected_idx]
            
            # Check if stealing
            if selected_driver.get('assigned_vehicle') and selected_driver['assigned_vehicle'] != vehicle_id:
                reply = QMessageBox.question(
                    self, 
                    "Reassign Driver?",
                    f"Driver '{selected_driver['name']}' is already assigned to another vehicle.\n"
                    "Do you want to reassign them to this vehicle?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return

            # Perform Assignment
            self.vehicle_manager.assign_driver(vehicle_id, selected_driver['id'], selected_driver['name'])
            self.driver_manager.assign_to_vehicle(selected_driver['id'], vehicle_id, vehicle_name)
            
            self.load_data()
            QMessageBox.information(self, "Success", f"Assigned '{selected_driver['name']}' to '{vehicle_name}'")
            
        elif getattr(dialog, 'unassign_requested', False):
            # Unassign pressed
            confirm = QMessageBox.question(
                self, "Confirm Unassign", 
                f"Remove driver '{current_driver_name}' from '{vehicle_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                # Find current driver ID to update their history
                # We need to know WHO was assigned. 
                # The table might not have ID, but vehicle object does.
                veh_obj = self.vehicle_manager.get_vehicle(vehicle_id)
                if veh_obj and veh_obj.get('driver_id'):
                    d_id = veh_obj['driver_id']
                    # Unassign in both managers
                    self.vehicle_manager.assign_driver(vehicle_id, None, None)
                    self.driver_manager.assign_to_vehicle(d_id, None, None)
                    
                    self.load_data()
                    QMessageBox.information(self, "Success", "Driver unassigned.")
    
    def change_vehicle_status(self):
        """Change status of selected vehicle"""
        row = self.vehicles_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a vehicle")
            return
        
        vehicle_id = self.vehicles_table.item(row, 5).text()
        vehicle_name = self.vehicles_table.item(row, 0).text()
        
        statuses = ["Active", "Maintenance", "Defective", "Inactive"]
        status, ok = QInputDialog.getItem(
            self,
            "Change Status",
            f"Select new status for '{vehicle_name}':",
            statuses,
            0,
            False
        )
        
        if ok and status:
            note, ok2 = QInputDialog.getText(
                self,
                "Status Note",
                "Enter note (optional):"
            )
            
            self.vehicle_manager.update_vehicle(
                vehicle_id,
                status=status.lower(),
                status_note=note if ok2 else None
            )
            self.load_vehicles()
            QMessageBox.information(self, "Success", f"Status changed to '{status}'")

    def add_vehicle_event(self):
        """Add a manual event (transit, maintenance, etc) to vehicle history"""
        row = self.vehicles_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a vehicle")
            return
            
        vehicle_id = self.vehicles_table.item(row, 5).text()
        
        # Get city list for transit
        from src.data.city_data_manager import CityDataManager
        cities = CityDataManager().get_all_cities()
        city_names = sorted(cities)
        
        dialog = VehicleEventDialog(self, city_names=city_names)
        if dialog.exec():
            data = dialog.get_data()
            
            # Add to manager
            start = data['start'].toPyDate()
            end = data['end'].toPyDate()
            
            if self.vehicle_manager.add_schedule(
                vehicle_id,
                start, 
                end, 
                data['type'], 
                data['origin'],
                data['destination'],
                data['details']
            ):
                QMessageBox.information(self, "Success", "Event added to history")
            else:
                QMessageBox.critical(self, "Error", "Failed to add event")

    def view_vehicle_history(self):
        """View assignment and event history for selected vehicle"""
        row = self.vehicles_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a vehicle")
            return
        
        vehicle_id = self.vehicles_table.item(row, 5).text()
        vehicle_name = self.vehicles_table.item(row, 0).text()
        
        # Get assignments (needs inverse lookup or update vehicle manager?)
        # VehicleManager doesn't store assignment history directly, DriverAssignmentHistory does.
        # But we can query DriverAssignmentHistory by vehicle_id. 
        # Actually DriverAssignmentHistory has vehicle_id.
        # I need a method in DriverManager or VehicleManager to get assignments for a VEHICLE.
        # Let's add it to VehicleManager or use direct query if needed. 
        # Better: Add `get_vehicle_assignment_history` to DriverManager or VehicleManager.
        # Since DriverAssignmentHistory is in models, let's assume we can fetch it.
        # For now, I'll fetch ALL driver histories and filter? No that's inefficient.
        # I'll rely on `get_vehicle_schedules` for now and maybe I need to add `get_history` to VehicleManager.
        # Wait, I didn't add assignment history fetching to VehicleManager in step 1.
        # I'll check if I can just show Schedules for now, or if I need assignments too.
        # The user asked for "masina in tranzit...".
        # Assignments are important.
        # I'll hack it: I'll fetch all drivers and check their history? No.
        # I should have added `get_assignments` to VehicleManager. 
        # I will assume I can add it now or query it.
        # Let's start with just Schedules (Events) as requested primarily.
        
        schedules = self.vehicle_manager.get_vehicle_schedules(vehicle_id)
        
        # Merge if we had assignments.
        combined_history = []
        for s in schedules:
            t = s['type'].replace('_', ' ').capitalize()
            if t == 'Transit':
                name = f"Transit: {s.get('origin','?')} -> {s.get('destination','?')}"
            else:
                name = f"Event: {t}"
                
            combined_history.append({
                'type': 'event',
                'name': name,
                'start_date': s.get('start', '').isoformat() if hasattr(s.get('start'), 'isoformat') else str(s.get('start')),
                'end_date': s.get('end', '').isoformat() if hasattr(s.get('end'), 'isoformat') else str(s.get('end')),
                'details': s.get('details', '')
            })
            
        combined_history.sort(key=lambda x: x.get('start_date') or "", reverse=True)
        
        dialog = VehicleHistoryDialog(self, vehicle_name, combined_history)
        dialog.exec()
    
    # Driver operations
    def add_driver(self):
        """Add a new driver"""
        dialog = DriverEditDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            self.driver_manager.add_driver(
                data['name'],
                data['phone'],
                data['license'],
                data['status']
            )
            self.load_drivers()
            QMessageBox.information(self, "Success", "Driver added successfully")
    
    def edit_driver(self):
        """Edit selected driver"""
        row = self.drivers_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a driver to edit")
            return
        
        driver_id = self.drivers_table.item(row, 5).text()
        driver = self.driver_manager.get_driver(driver_id)
        
        if not driver:
            QMessageBox.critical(self, "Error", "Driver not found")
            return
        
        dialog = DriverEditDialog(self, driver)
        if dialog.exec():
            data = dialog.get_data()
            self.driver_manager.update_driver(
                driver_id,
                data['name'],
                data['phone'],
                data['license'],
                data['status']
            )
            self.load_drivers()
            QMessageBox.information(self, "Success", "Driver updated successfully")
    
    def delete_driver(self):
        """Delete selected driver"""
        row = self.drivers_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a driver to delete")
            return
        
        driver_id = self.drivers_table.item(row, 5).text()
        driver_name = self.drivers_table.item(row, 0).text()
        driver = self.driver_manager.get_driver(driver_id)
        
        if driver and driver.get('assigned_vehicle'):
            QMessageBox.critical(
                self,
                "Cannot Delete",
                f"Driver '{driver_name}' is assigned to a vehicle.\nUnassign first."
            )
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete driver '{driver_name}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.driver_manager.delete_driver(driver_id):
                self.load_drivers()
                QMessageBox.information(self, "Success", "Driver deleted successfully")
            else:
                QMessageBox.critical(self, "Error", "Failed to delete driver")
    
    def view_driver_history(self):
        """View assignment history for selected driver"""
        row = self.drivers_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a driver")
            return
        
        driver_id = self.drivers_table.item(row, 5).text()
        driver_name = self.drivers_table.item(row, 0).text()
        
        history = self.driver_manager.get_driver_history(driver_id)
        schedules = self.driver_manager.get_driver_schedules(driver_id)
        
        if not history and not schedules:
            QMessageBox.information(self, "No History", f"No assignment history for '{driver_name}'")
            return
            
        # Merge and Sort
        # Assignments have: vehicle_name, start_date (iso), end_date (iso)
        # Schedules have: event_type, details, start_date (iso), end_date (iso)
        
        combined_history = []
        
        for h in history:
            combined_history.append({
                'type': 'assignment',
                'name': h.get('vehicle_name', 'Unknown Vehicle'),
                'start_date': h.get('start_date'),
                'end_date': h.get('end_date'),
                'details': ''
            })
            
        for s in schedules:
            # Format event name
            evt_name = f"Leave: {s['event_type'].capitalize()}"
            if s.get('details'):
                 evt_name += f" ({s['details']})"
                 
            combined_history.append({
                'type': 'event',
                'name': evt_name,
                'start_date': s.get('start_date'),
                'end_date': s.get('end_date'),
                'details': s.get('details', '')
            })
            
        # Sort by start_date desc
        combined_history.sort(key=lambda x: x.get('start_date') or "", reverse=True)
        
        # Open History Dialog
        dialog = DriverHistoryDialog(self, driver_name, combined_history)
        dialog.exec()

    def add_driver_event(self):
        """Add a manual event (leave, medical, etc) to driver history"""
        row = self.drivers_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a driver")
            return
            
        driver_id = self.drivers_table.item(row, 5).text()
        
        dialog = DriverEventDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            
            # Add to manager
            # Convert QDate to python date
            start = data['start'].toPyDate()
            end = data['end'].toPyDate()
            
            if self.driver_manager.add_driver_schedule(
                driver_id,
                start, 
                end, 
                data['type'], 
                data['details']
            ):
                QMessageBox.information(self, "Success", "Event added to history")
            else:
                QMessageBox.critical(self, "Error", "Failed to add event")

    def manage_driver_assignment(self):
        """Manage vehicle assignment for selected driver"""
        row = self.drivers_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a driver")
            return
            
        driver_id = self.drivers_table.item(row, 5).text()
        driver_name = self.drivers_table.item(row, 0).text()
        current_vehicle_name = self.drivers_table.item(row, 3).text()
        
        has_vehicle = current_vehicle_name != "Unassigned"
        
        # Get all active vehicles
        all_vehicles = self.vehicle_manager.get_active_vehicles()
        if not all_vehicles:
            QMessageBox.warning(self, "No Vehicles", "No active vehicles available")
            return
            
        # Prepare list
        vehicle_options = []
        current_vehicle_idx = 0
        
        for i, v in enumerate(all_vehicles):
            status = ""
            if v.get('driver_id'):
                d_name = v.get('driver_name', 'Unknown')
                # If assigned to THIS driver
                if v['driver_id'] == driver_id:
                    current_vehicle_idx = i
                    status = " [Current Assignment]"
                else:
                    status = f" [Assigned to: {d_name}]"
            
            vehicle_options.append(f"{v['name']} ({v.get('registration', '-').upper()}){status}")
            
        # UI Dialog
        from PyQt6.QtWidgets import QVBoxLayout, QLabel, QComboBox, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Manage Vehicle for '{driver_name}'")
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel(f"Current Vehicle: {current_vehicle_name}"))
        layout.addWidget(QLabel("Select Vehicle:"))
        
        combo = QComboBox()
        combo.addItems(vehicle_options)
        if has_vehicle:
            # Need to find independent of list order if possible, but loop above sets index
            # verify if 'Unassigned' logic in loop matches
             pass
        # Logic to set index based on driver match is handled in loop? 
        # Actually loop sets current_vehicle_idx if match found.
        # But if current driver has vehicle, and we iterate ALL vehicles, we should find it.
        
        # Wait, if driver says "assigned to X", X must be in all_vehicles if active.
        # So current_vehicle_idx logic in loop is correct.
        
        combo.setCurrentIndex(current_vehicle_idx)
            
        layout.addWidget(combo)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        
        unassign_btn = None
        if has_vehicle:
            unassign_btn = btn_box.addButton("Unassign Vehicle", QDialogButtonBox.ButtonRole.DestructiveRole)
            
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)
        
        # Track unassign action
        dialog.unassign_requested = False
        def on_unassign():
            dialog.unassign_requested = True
            dialog.reject()
            
        if unassign_btn:
            unassign_btn.clicked.connect(on_unassign)
        
        # Execute
        dialog.exec()
        
        if dialog.result() == QDialog.DialogCode.Accepted:
            selected_idx = combo.currentIndex()
            selected_vehicle = all_vehicles[selected_idx]
            
            # Check if stealing
            if selected_vehicle.get('driver_id') and selected_vehicle['driver_id'] != driver_id:
                reply = QMessageBox.question(
                    self,
                    "Reassign Vehicle?",
                    f"Vehicle '{selected_vehicle['name']}' is already assigned to {selected_vehicle.get('driver_name')}.\n"
                    "Do you want to reassign it to this driver?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
            
            # Perform Assignment
            self.vehicle_manager.assign_driver(selected_vehicle['id'], driver_id, driver_name)
            self.driver_manager.assign_to_vehicle(driver_id, selected_vehicle['id'], selected_vehicle['name'])
            
            self.load_data()
            QMessageBox.information(self, "Success", f"Assigned '{driver_name}' to '{selected_vehicle['name']}'")
            
        elif getattr(dialog, 'unassign_requested', False):
             confirm = QMessageBox.question(
                self, "Confirm Unassign", 
                f"Remove driver '{driver_name}' from '{current_vehicle_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
             if confirm == QMessageBox.StandardButton.Yes:
                 # Find vehicle ID
                 drv_obj = self.driver_manager.get_driver(driver_id)
                 if drv_obj and drv_obj.get('assigned_vehicle'):
                     v_id = drv_obj['assigned_vehicle']
                     self.vehicle_manager.assign_driver(v_id, None, None)
                     self.driver_manager.assign_to_vehicle(driver_id, None, None)
                     
                     self.load_data()
                     QMessageBox.information(self, "Success", "Vehicle unassigned.")


class VehicleEditDialog(QDialog):
    """Dialog for adding/editing vehicles with Documents tab"""
    
    def __init__(self, parent=None, vehicle=None):
        super().__init__(parent)
        self.vehicle = vehicle
        self.setWindowTitle("Edit Vehicle" if vehicle else "Add Vehicle")
        self.resize(500, 400)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Mașina 1")
        form_layout.addRow("Name:", self.name_input)
        
        self.registration_input = QLineEdit()
        self.registration_input.setPlaceholderText("e.g., B-123-ABC")
        form_layout.addRow("Registration:", self.registration_input)
        
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "Maintenance", "Defective", "Inactive"])
        form_layout.addRow("Status:", self.status_combo)
        
        layout.addLayout(form_layout)
        
        # Manage Documents Button
        if self.vehicle:  # Only show for existing vehicles
            docs_btn = QPushButton("📄 Manage Documents")
            docs_btn.setStyleSheet("padding: 10px; font-size: 12px;")
            docs_btn.clicked.connect(self.manage_documents)
            layout.addWidget(docs_btn)
        
        # Load existing data
        if self.vehicle:
            self.name_input.setText(self.vehicle.get('name', ''))
            self.registration_input.setText(self.vehicle.get('registration', ''))
            status = self.vehicle.get('status', 'active').capitalize()
            self.status_combo.setCurrentText(status)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def manage_documents(self):
        """Open document management dialog"""
        from src.ui.document_management_dialog import DocumentManagementDialog
        
        vehicle_id = self.vehicle.get('id')
        vehicle_name = self.vehicle.get('name', 'Unknown')
        
        dialog = DocumentManagementDialog(
            self,
            entity_type='vehicle',
            entity_id=vehicle_id,
            entity_name=vehicle_name
        )
        dialog.exec()
    
    def get_data(self):
        return {
            'name': self.name_input.text().strip(),
            'registration': self.registration_input.text().strip(),
            'status': self.status_combo.currentText().lower()
        }


class DriverEditDialog(QDialog):
    """Dialog for adding/editing drivers"""
    
    def __init__(self, parent=None, driver=None):
        super().__init__(parent)
        self.driver = driver
        self.setWindowTitle("Edit Driver" if driver else "Add Driver")
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Ion Popescu")
        form_layout.addRow("Name:", self.name_input)
        
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("e.g., 0721234567")
        form_layout.addRow("Phone:", self.phone_input)
        
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("e.g., AB123456")
        form_layout.addRow("License Number:", self.license_input)
        
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "Inactive"])
        form_layout.addRow("Status:", self.status_combo)
        
        layout.addLayout(form_layout)
        
        # Manage Documents Button
        if self.driver:  # Only show for existing drivers
            docs_btn = QPushButton("📄 Manage Documents")
            docs_btn.setStyleSheet("padding: 10px; font-size: 12px;")
            docs_btn.clicked.connect(self.manage_documents)
            layout.addWidget(docs_btn)
        
        # Load existing data
        if self.driver:
            self.name_input.setText(self.driver.get('name', ''))
            self.phone_input.setText(self.driver.get('phone', ''))
            self.license_input.setText(self.driver.get('license_number', ''))
            status = self.driver.get('status', 'active').capitalize()
            self.status_combo.setCurrentText(status)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def manage_documents(self):
        """Open document management dialog"""
        from src.ui.document_management_dialog import DocumentManagementDialog
        
        driver_id = self.driver.get('id')
        driver_name = self.driver.get('name', 'Unknown')
        
        dialog = DocumentManagementDialog(
            self,
            entity_type='driver',
            entity_id=driver_id,
            entity_name=driver_name
        )
        dialog.exec()
    
    def get_data(self):
        return {
            'name': self.name_input.text().strip(),
            'phone': self.phone_input.text().strip(),
            'license': self.license_input.text().strip(),
            'status': self.status_combo.currentText().lower()
        }


class DriverEventDialog(QDialog):
    """Dialog for adding driver events (leaves, etc)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Driver Event")
        self.resize(400, 300)
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout(self)
        from PyQt6.QtWidgets import QDateEdit
        from PyQt6.QtCore import QDate
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Vacation", "Medical Leave", "Unpaid Leave", "Free Day", "Other"])
        layout.addRow("Event Type:", self.type_combo)
        
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())
        layout.addRow("Start Date:", self.start_date)
        
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        layout.addRow("End Date:", self.end_date)
        
        self.details = QLineEdit()
        layout.addRow("Details (Optional):", self.details)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
    def get_data(self):
        return {
            'type': self.type_combo.currentText().lower(),
            'start': self.start_date.date(),
            'end': self.end_date.date(),
            'details': self.details.text().strip()
        }


class DriverHistoryDialog(QDialog):
    """Dialog to view detailed driver assignment history"""
    
    def __init__(self, parent=None, driver_name="", history=None):
        super().__init__(parent)
        self.setWindowTitle(f"History - {driver_name}")
        self.resize(800, 500)
        self.history = history or []
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Summary Header
        header = QLabel(f"Assignment & Leave History ({len(self.history)} records)")
        header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Activity / Vehicle", "Start Date", "End Date", "Duration", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        layout.addWidget(self.table)
        
        self.populate_table()
        
        # Close button
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(self.accept)
        layout.addWidget(btn_box)
        
    def populate_table(self):
        self.table.setRowCount(len(self.history))
        
        from datetime import datetime
        
        for row, item in enumerate(self.history):
            start_str = item.get('start_date')
            end_str = item.get('end_date')
            
            # 1. Activity / Vehicle
            name = item.get('name', 'Unknown')
            self.table.setItem(row, 0, QTableWidgetItem(name))
            
            # 2. Start Date
            start_disp = start_str[:10] if start_str else "Unknown"
            # Show time only for assignments if present
            if 'T' in (start_str or ""):
                 start_time = start_str[11:16]
                 start_disp += f" {start_time}"
            self.table.setItem(row, 1, QTableWidgetItem(start_disp))
            
            # 3. End Date
            end_disp = "Present"
            status = "Current"
            if end_str:
                end_disp = end_str[:10]
                status = "Completed"
            
            self.table.setItem(row, 2, QTableWidgetItem(end_disp))
            
            # 4. Duration
            duration = "-"
            try:
                if start_str:
                    s_dt = datetime.fromisoformat(start_str)
                    if end_str:
                        e_dt = datetime.fromisoformat(end_str)
                    else:
                        e_dt = datetime.now()
                    
                    delta = e_dt - s_dt
                    parts = []
                    if delta.days > 0:
                        parts.append(f"{delta.days} days")
                    
                    hours = delta.seconds // 3600
                    if hours > 0:
                        parts.append(f"{hours}h")
                        
                    duration = ", ".join(parts) if parts else "< 1h"
            except:
                pass
                
            self.table.setItem(row, 3, QTableWidgetItem(duration))
            
            # 5. Status
            # If event, might use 'type'
            if item.get('type') == 'event':
                status = "Event"
                
            status_item = QTableWidgetItem(status)
            if status == "Current":
                status_item.setForeground(Qt.GlobalColor.darkGreen)
                f = status_item.font()
                f.setBold(True)
                status_item.setFont(f)
            elif status == "Event":
                status_item.setForeground(Qt.GlobalColor.blue)
                
            self.table.setItem(row, 4, status_item)

class VehicleEventDialog(QDialog):
    """Dialog for adding vehicle events (transit, maintenance, etc)"""
    def __init__(self, parent=None, city_names=None):
        super().__init__(parent)
        self.city_names = city_names or []
        self.setWindowTitle("Add Vehicle Event")
        self.resize(450, 400)
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout(self)
        from PyQt6.QtWidgets import QDateEdit, QStackedWidget
        from PyQt6.QtCore import QDate
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Transit", "Maintenance", "Defective", "No Docs", "Other"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        layout.addRow("Event Type:", self.type_combo)
        
        # Transit Cities (only for Transit)
        self.transit_widget = QWidget()
        t_layout = QFormLayout(self.transit_widget)
        
        self.origin_combo = QComboBox()
        self.origin_combo.setEditable(True)
        self.origin_combo.addItems(self.city_names)
        t_layout.addRow("From City:", self.origin_combo)
        
        self.dest_combo = QComboBox()
        self.dest_combo.setEditable(True)
        self.dest_combo.addItems(self.city_names)
        t_layout.addRow("To City:", self.dest_combo)
        
        layout.addRow(self.transit_widget)
        
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())
        layout.addRow("Start Date:", self.start_date)
        
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        layout.addRow("End Date:", self.end_date)
        
        self.details = QLineEdit()
        layout.addRow("Details/Note:", self.details)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        self.on_type_changed(self.type_combo.currentText())
        
    def on_type_changed(self, text):
        self.transit_widget.setVisible(text == "Transit")
        
    def get_data(self):
        return {
            'type': self.type_combo.currentText().lower(),
            'start': self.start_date.date(),
            'end': self.end_date.date(),
            'origin': self.origin_combo.currentText() if self.transit_widget.isVisible() else None,
            'destination': self.dest_combo.currentText() if self.transit_widget.isVisible() else None,
            'details': self.details.text().strip()
        }

class VehicleHistoryDialog(QDialog):
    """Dialog to view detailed vehicle history"""
    
    def __init__(self, parent=None, vehicle_name="", history=None):
        super().__init__(parent)
        self.setWindowTitle(f"History - {vehicle_name}")
        self.resize(800, 500)
        self.history = history or []
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Summary Header
        header = QLabel(f"Vehicle Activity History ({len(self.history)} records)")
        header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Event / Activity", "Start Date", "End Date", "Details"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        layout.addWidget(self.table)
        
        self.populate_table()
        
        # Close button
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(self.accept)
        layout.addWidget(btn_box)
        
    def populate_table(self):
        self.table.setRowCount(len(self.history))
        
        for row, item in enumerate(self.history):
            start_str = item.get('start_date')
            end_str = item.get('end_date')
            
            # 1. Name
            name = item.get('name', 'Unknown')
            self.table.setItem(row, 0, QTableWidgetItem(name))
            
            # 2. Start
            self.table.setItem(row, 1, QTableWidgetItem(start_str[:10] if start_str else ""))
            
            # 3. End
            self.table.setItem(row, 2, QTableWidgetItem(end_str[:10] if end_str else "Ongoing"))
            
            # 4. Details
            self.table.setItem(row, 3, QTableWidgetItem(item.get('details', '')))
