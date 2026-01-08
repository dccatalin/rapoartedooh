from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                              QDateEdit, QDialogButtonBox, QComboBox, QDoubleSpinBox, 
                              QSpinBox, QLabel, QGroupBox, QPushButton, QMessageBox, QHBoxLayout,
                              QCheckBox, QTextEdit, QApplication, QListWidget, QListWidgetItem, QFileDialog,
                              QProgressDialog, QToolBox, QWidget, QMenu, QTimeEdit,
                              QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView)
from PyQt6.QtCore import QDate, Qt, QTime
import datetime
from src.data.city_data_manager import CityDataManager
from src.data.vehicle_manager import VehicleManager
from src.ui.custom_schedule_dialog import CustomScheduleDialog
from src.ui.custom_distance_dialog import CustomDistanceDialog
from src.utils.kml_parser import parse_kml
from src.data.campaign_storage import CampaignStorage
from src.utils.validators import CampaignValidator
import os

from src.ui.city_periods_dialog import CityPeriodsDialog
from src.ui.campaign_calendar_view import CampaignCalendarView
from src.ui.city_update_confirmation_dialog import CityUpdateConfirmationDialog
from src.ui.city_update_preferences_dialog import CityUpdatePreferencesDialog
from src.ui.vehicle_config_dialog import VehicleConfigDialog


class CampaignReportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mobile DOOH Campaign Details")
        self.resize(500, 700)
        self.city_manager = CityDataManager()
        self.storage = CampaignStorage()
        self.vehicle_manager = VehicleManager()
        self.current_campaign_id = None
        
        # Initialize attributes that will be set later
        self.custom_schedule = {}
        self.custom_distance_km = 0
        self.city_periods = {}
        self.city_schedules = {}
        self.route_data = None
        self.should_generate_report = False
        
        self.init_ui()
        self.center_on_screen()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        load_btn = QPushButton("Load Campaign")
        load_btn.clicked.connect(self.show_load_menu)
        toolbar_layout.addWidget(load_btn)
        
        draft_btn = QPushButton("Save Draft")
        draft_btn.clicked.connect(self.save_draft)
        toolbar_layout.addWidget(draft_btn)
        
        new_btn = QPushButton("Save As New")
        new_btn.clicked.connect(self.save_as_new)
        toolbar_layout.addWidget(new_btn)
        
        toolbar_layout.addStretch()
        main_layout.addLayout(toolbar_layout)

        self.toolbox = QToolBox()
        
        # --- PAGE 1: General Info & Schedule ---
        page1 = QWidget()
        layout1 = QFormLayout(page1)
        
        # Basics
        self.client_name = QLineEdit()
        self.client_name.setPlaceholderText("Client Name")
        layout1.addRow("Client:", self.client_name)
        self.client_input = self.client_name # alias
        
        self.campaign_name = QLineEdit()
        self.campaign_name.setPlaceholderText("Campaign Name")
        layout1.addRow("Campaign:", self.campaign_name)
        self.campaign_input = self.campaign_name # alias
        self.name_input = self.campaign_name # alias
        
        self.po_number = QLineEdit()
        self.po_number.setPlaceholderText("PO Number (Optional)")
        layout1.addRow("PO Number:", self.po_number)
        
        # Schedule (Moved from separate page)
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-7))
        layout1.addRow("Start Date:", self.start_date)
        
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        layout1.addRow("End Date:", self.end_date)
        
        # Daily Hours
        self.hours_start = QTimeEdit()
        self.hours_start.setDisplayFormat("HH:mm")
        self.hours_start.setTime(QTime(9, 0))
        
        self.hours_end = QTimeEdit()
        self.hours_end.setDisplayFormat("HH:mm")
        self.hours_end.setTime(QTime(17, 0))
        
        daily_hours_layout = QHBoxLayout()
        daily_hours_layout.addWidget(QLabel("From:"))
        daily_hours_layout.addWidget(self.hours_start)
        daily_hours_layout.addWidget(QLabel("To:"))
        daily_hours_layout.addWidget(self.hours_end)
        
        custom_schedule_btn = QPushButton("Orar Diferentiat")
        custom_schedule_btn.setMaximumWidth(120)
        custom_schedule_btn.setToolTip("Defineste orar diferit pentru fiecare zi")
        custom_schedule_btn.clicked.connect(self.set_custom_schedule)
        daily_hours_layout.addWidget(custom_schedule_btn)
        
        layout1.addRow("Daily Hours:", daily_hours_layout)
        self.custom_daily_schedule = None
        
        # Status
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Confirmed", "Reserved", "Canceled"])
        layout1.addRow("Status:", self.status_combo)
        
        self.toolbox.addItem(page1, "1. General Information & Schedule")

        # --- PAGE 2: Assigned Vehicles & Parameters ---
        page2 = QWidget()
        layout2 = QVBoxLayout(page2)
        
        # Vehicle List
        self.vehicle_table = QTableWidget()
        self.vehicle_table.setColumnCount(4)
        self.vehicle_table.setHorizontalHeaderLabels(["Vehicle", "Driver", "Config", "Cities"])
        self.vehicle_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.vehicle_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.vehicle_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.vehicle_table.doubleClicked.connect(self.edit_vehicle)
        layout2.addWidget(self.vehicle_table)
        
        # Vehicle Buttons
        v_btn_layout = QHBoxLayout()
        
        add_v_btn = QPushButton("Add Vehicle")
        add_v_btn.clicked.connect(self.add_vehicle)
        v_btn_layout.addWidget(add_v_btn)
        
        edit_v_btn = QPushButton("Edit Vehicle")
        edit_v_btn.clicked.connect(self.edit_vehicle)
        v_btn_layout.addWidget(edit_v_btn)
        
        rem_v_btn = QPushButton("Remove Vehicle")
        rem_v_btn.clicked.connect(self.remove_vehicle)
        v_btn_layout.addWidget(rem_v_btn)
        
        v_btn_layout.addStretch()
        layout2.addLayout(v_btn_layout)
        
        # Vehicle Parameters (Global/Default)
        param_group = QGroupBox("Global Vehicle Parameters (Defaults)")
        param_layout = QFormLayout()
        
        self.speed = QSpinBox()
        self.speed.setRange(1, 100)
        self.speed.setValue(25)
        self.speed.setSuffix(" km/h")
        param_layout.addRow("Average Speed:", self.speed)
        
        self.stationing = QSpinBox()
        self.stationing.setRange(0, 60)
        self.stationing.setValue(15)
        self.stationing.setSuffix(" min/hour")
        param_layout.addRow("Stationing Time:", self.stationing)
        
        # Distance (Moved from Page 4)
        self.use_known_distance = QCheckBox("Use Known Total Distance")
        self.use_known_distance.setToolTip("Bifati daca cunoasteti distanta parcursa")
        self.use_known_distance.toggled.connect(self.toggle_distance_input)
        param_layout.addRow("", self.use_known_distance)
        
        self.distance_total = QDoubleSpinBox()
        self.distance_total.setRange(0, 10000)
        self.distance_total.setValue(0)
        self.distance_total.setSuffix(" km (total)")
        self.distance_total.setEnabled(False)
        self.distance_total.valueChanged.connect(self.update_roi_display)
        param_layout.addRow("Distanta Totala:", self.distance_total)
        
        # Custom daily distances
        distance_daily_layout = QHBoxLayout()
        self.distance_daily_label = QLabel("Nu este setat")
        self.distance_daily_label.setStyleSheet("color: #666;")
        distance_daily_layout.addWidget(self.distance_daily_label)
        
        custom_distance_btn = QPushButton("Distante pe Zile")
        custom_distance_btn.setMaximumWidth(120)
        custom_distance_btn.clicked.connect(self.set_custom_distances)
        distance_daily_layout.addWidget(custom_distance_btn)
        
        param_layout.addRow("Distante Zilnice:", distance_daily_layout)
        self.custom_daily_distances = None
        
        param_group.setLayout(param_layout)
        layout2.addWidget(param_group)
        
        self.toolbox.addItem(page2, "2. Assigned Vehicles & Parameters")
        
        # Initialize internal vehicle list
        self.assigned_vehicles = [] # List of dicts

        # --- PAGE 3: Target Cities & Route ---
        page3 = QWidget()
        layout3 = QVBoxLayout(page3)
        
        group_city = QGroupBox("Target Cities & Periods")
        layout_city = QVBoxLayout()
        
        self.city_list = QListWidget()
        self.city_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.city_list.setMaximumHeight(100)
        self.load_cities()
        layout_city.addWidget(self.city_list)
        
        self.city_periods_btn = QPushButton("Set City Periods & Schedules")
        self.city_periods_btn.clicked.connect(self.open_city_periods)
        layout_city.addWidget(self.city_periods_btn)
        
        city_btn_layout = QHBoxLayout()
        add_city_btn = QPushButton("Add New City")
        add_city_btn.clicked.connect(self.add_new_city)
        city_btn_layout.addWidget(add_city_btn)
        
        refresh_btn = QPushButton("Refresh Data")
        refresh_btn.clicked.connect(self.refresh_data)
        city_btn_layout.addWidget(refresh_btn)
        
        prefs_btn = QPushButton("Update Preferences")
        prefs_btn.clicked.connect(self.open_update_preferences)
        city_btn_layout.addWidget(prefs_btn)
        
        layout_city.addLayout(city_btn_layout)
        group_city.setLayout(layout_city)
        layout3.addWidget(group_city)
        
        # Route
        route_group = QGroupBox("Route & Location Context")
        route_layout = QFormLayout()
        
        self.pois_input = QTextEdit()
        self.pois_input.setPlaceholderText("Enter Points of Interest (one per line)\\ne.g. Piata Unirii\\nMall Vitan")
        self.pois_input.setMaximumHeight(60)
        route_layout.addRow("Points of Interest:", self.pois_input)
        
        kml_layout = QHBoxLayout()
        self.kml_btn = QPushButton("Import Route (KML)")
        self.kml_btn.clicked.connect(self.import_kml)
        kml_layout.addWidget(self.kml_btn)
        
        self.distance_label = QLabel("Distance: -")
        kml_layout.addWidget(self.distance_label)
        
        route_layout.addRow("Route:", kml_layout)
        self.route_data = None
        
        route_group.setLayout(route_layout)
        layout3.addWidget(route_group)
        
        self.toolbox.addItem(page3, "3. Target Cities & Route")

        # --- PAGE 4: Spot Settings ---
        page4 = QWidget()
        layout4 = QFormLayout(page4)
        
        self.spot_duration = QSpinBox()
        self.spot_duration.setRange(1, 300)
        self.spot_duration.setValue(10)
        self.spot_duration.setSuffix(" sec")
        layout4.addRow("Spot Duration:", self.spot_duration)
        
        # Campaign Type
        from PyQt6.QtWidgets import QRadioButton, QButtonGroup
        self.type_bg = QButtonGroup(self)
        
        self.radio_loop = QRadioButton("Loop Campaign (Shared)")
        self.radio_loop.setChecked(True)
        
        self.radio_exclusive = QRadioButton("Exclusive Campaign")
        
        self.type_bg.addButton(self.radio_loop)
        self.type_bg.addButton(self.radio_exclusive)
        
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.radio_loop)
        radio_layout.addWidget(self.radio_exclusive)
        layout4.addRow("Campaign Type:", radio_layout)
        
        self.loop_duration = QSpinBox()
        self.loop_duration.setRange(10, 3600)
        self.loop_duration.setValue(60)
        self.loop_duration.setSuffix(" sec")
        layout4.addRow("Loop Duration:", self.loop_duration)
        
        self.radio_exclusive.toggled.connect(self.toggle_loop_input)
        
        self.toolbox.addItem(page4, "4. Spot Settings")
        
        # --- Section 5: Financial Details ---
        page5 = QWidget()
        layout5 = QFormLayout(page5)
        
        self.cost_per_km = QDoubleSpinBox()
        self.cost_per_km.setRange(0, 1000)
        self.cost_per_km.setValue(0)
        self.cost_per_km.setDecimals(2)
        self.cost_per_km.setSuffix(" €/km")
        self.cost_per_km.setToolTip("Cost per kilometer driven")
        layout5.addRow("Cost per km:", self.cost_per_km)
        
        self.fixed_costs = QDoubleSpinBox()
        self.fixed_costs.setRange(0, 1000000)
        self.fixed_costs.setValue(0)
        self.fixed_costs.setDecimals(2)
        self.fixed_costs.setSuffix(" €")
        self.fixed_costs.setToolTip("Fixed costs (setup, design, etc.)")
        layout5.addRow("Fixed Costs:", self.fixed_costs)
        
        self.expected_revenue = QDoubleSpinBox()
        self.expected_revenue.setRange(0, 1000000)
        self.expected_revenue.setValue(0)
        self.expected_revenue.setDecimals(2)
        self.expected_revenue.setSuffix(" €")
        self.expected_revenue.setToolTip("Expected revenue from campaign")
        layout5.addRow("Expected Revenue:", self.expected_revenue)
        
        # ROI Display (read-only)
        self.roi_label = QLabel("ROI: N/A")
        self.roi_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        layout5.addRow("Estimated ROI:", self.roi_label)
        
        # Connect signals to update ROI
        self.cost_per_km.valueChanged.connect(self.update_roi_display)
        self.fixed_costs.valueChanged.connect(self.update_roi_display)
        self.expected_revenue.valueChanged.connect(self.update_roi_display)
        
        self.toolbox.addItem(page5, "5. Financial Details")
        
        main_layout.addWidget(self.toolbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save Campaign")
        save_btn.setToolTip("Save the campaign data and close without generating a report.")
        save_btn.clicked.connect(self.save_and_close)
        button_layout.addWidget(save_btn)
        
        generate_btn = QPushButton("Generate Report")
        generate_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 6px 16px;")
        generate_btn.setToolTip("Save the campaign and generate the PDF report immediately.")
        generate_btn.clicked.connect(self.save_and_generate)
        button_layout.addWidget(generate_btn)
        
        main_layout.addLayout(button_layout)
        
    def save_and_close(self):
        """Save campaign and close without generating report"""
        if self.validate_inputs():
            data = self.get_data()
            campaign_id = self.storage.save_campaign(data, self.current_campaign_id)
            self.current_campaign_id = campaign_id
            self.should_generate_report = False
            super().accept()
            
    def save_and_generate(self):
        """Save campaign and close ensuring report generation triggers"""
        if self.validate_inputs():
            data = self.get_data()
            campaign_id = self.storage.save_campaign(data, self.current_campaign_id)
            self.current_campaign_id = campaign_id
            self.should_generate_report = True
            super().accept()
    
    def add_vehicle(self):
        """Open dialog to add a vehicle"""
        dialog = VehicleConfigDialog(self)
        if dialog.exec():
            config = dialog.get_vehicle_config()
            # Check for duplicates?
            for v in self.assigned_vehicles:
                if v['vehicle_id'] == config['vehicle_id']:
                    QMessageBox.warning(self, "Duplicate", "This vehicle is already assigned.")
                    return
            
            self.assigned_vehicles.append(config)
            self.refresh_vehicle_table()
            self.sync_vehicle_cities()
            
    def edit_vehicle(self):
        """Edit selected vehicle"""
        row = self.vehicle_table.currentRow()
        if row < 0:
            return
            
        data = self.assigned_vehicles[row]
        dialog = VehicleConfigDialog(self, vehicle_data=data)
        if dialog.exec():
            config = dialog.get_vehicle_config()
            self.assigned_vehicles[row] = config
            self.refresh_vehicle_table()
            self.sync_vehicle_cities()
            
    def remove_vehicle(self):
        """Remove selected vehicle"""
        row = self.vehicle_table.currentRow()
        if row >= 0:
            del self.assigned_vehicles[row]
            self.refresh_vehicle_table()
            self.sync_vehicle_cities()
            
    def sync_vehicle_cities(self):
        """Auto-select cities that are assigned to vehicles"""
        cities_to_select = set()
        for v in self.assigned_vehicles:
            if v.get('override_cities'):
                for city in v.get('cities', []):
                    cities_to_select.add(city)
                    
        # Select them in the list if not already selected
        for i in range(self.city_list.count()):
            item = self.city_list.item(i)
            # Use UserRole for raw city name (ignores county suffix in text)
            city_name = item.data(Qt.ItemDataRole.UserRole)
            if city_name in cities_to_select:
                item.setSelected(True)
            
    def refresh_vehicle_table(self):
        """Refresh the table from self.assigned_vehicles"""
        self.vehicle_table.setRowCount(0)
        
        for i, v in enumerate(self.assigned_vehicles):
            self.vehicle_table.insertRow(i)
            
            # Name
            name = v.get('vehicle_name', 'Unknown')
            self.vehicle_table.setItem(i, 0, QTableWidgetItem(name))
            
            # Driver
            driver = v.get('driver_name', 'No Driver')
            self.vehicle_table.setItem(i, 1, QTableWidgetItem(driver))
            
            # Config
            config_strs = []
            if v.get('override_cities'):
                config_strs.append(f"Cities: {len(v.get('cities', []))}")
            else:
                config_strs.append("Global Cities")
                
            self.vehicle_table.setItem(i, 2, QTableWidgetItem(", ".join(config_strs)))
            
            # Cities tooltip or simple column
            cities = v.get('cities', [])
            cities_str = ", ".join(cities) if v.get('override_cities') else "Default"
            self.vehicle_table.setItem(i, 3, QTableWidgetItem(cities_str))
            
    def update_vehicle_status(self):
        # Deprecated
        pass

    def validate_inputs(self):
        """Validate all inputs before saving"""
        # Basic validations
        if not self.client_name.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a client name")
            return False
            
        if not self.campaign_name.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a campaign name")
            return False
            
        # Vehicle validation
        if not self.assigned_vehicles:
            QMessageBox.warning(self, "Validation Error", "Please assign at least one vehicle")
            return False
            
        # City validation (Global)
        selected_cities = []
        for i in range(self.city_list.count()):
            item = self.city_list.item(i)
            if item.isSelected():
                selected_cities.append(item.data(Qt.ItemDataRole.UserRole))
                
        if not selected_cities and not any(v.get('override_cities') for v in self.assigned_vehicles):
            QMessageBox.warning(self, "Validation Error", "Please select at least one global city or configure specific cities for all vehicles.")
            return False
            
        return True
        
    def accept(self):
        """Override accept to validate inputs first"""
        if self.validate_inputs():
            super().accept()
        
        
        # Connect Tab Change
        self.toolbox.currentChanged.connect(self.on_tab_changed)
        
    def on_tab_changed(self, index):
        """Handle tab changes (auto-save and sync)"""
        # Always sync vehicle cities to be sure
        self.sync_vehicle_cities()
        
        # Auto-save draft silently
        # We only save if we have at least basic info (client/campaign name)
        # to avoid cluttering DB with empty drafts if user just browsing
        if self.client_name.text() and self.campaign_name.text():
            self.save_draft(silent=True)

    def save_draft(self, silent=False):
        """Save current campaign as draft"""
        data = self.get_data()
        try:
            campaign_id = self.storage.save_campaign(data, self.current_campaign_id)
            self.current_campaign_id = campaign_id
            if not silent:
                QMessageBox.information(self, "Saved", "Campaign saved successfully.")
        except Exception as e:
            if not silent:
                QMessageBox.warning(self, "Error", f"Could not save draft: {e}")
            else:
                print(f"Auto-save failed: {e}")
    
    def save_as_new(self):
        """Save current campaign as a new campaign (always creates new ID)"""
        data = self.get_data()
        # Pass None as campaign_id to force creation of new campaign
        campaign_id = self.storage.save_campaign(data, None)
        self.current_campaign_id = campaign_id
        QMessageBox.information(self, "Saved As New", f"New campaign created successfully!\n\nCampaign ID: {campaign_id[:8]}...")
        
    def show_load_menu(self):
        """Show dialog to load campaigns"""
        from src.ui.campaign_selection_dialog import CampaignSelectionDialog
        
        dialog = CampaignSelectionDialog(self)
        if dialog.exec():
            camp_id = dialog.get_selected_id()
            if camp_id:
                campaign = self.storage.get_campaign(camp_id)
                if campaign:
                    self.load_campaign(campaign)
                    
    # Alias for button connection if needed, or just rename the slot above
    show_load_dialog = show_load_menu
        
    def load_campaign(self, data):
        """Load campaign data into UI"""
        self.current_campaign_id = data.get('id')
        self.set_data(data)

    def set_data(self, data):
        """Populate UI with data"""
        self.client_name.setText(data.get('client_name') or '')
        self.campaign_name.setText(data.get('campaign_name') or '')
        self.po_number.setText(data.get('po_number') or '')
        
        # Set dates
        if isinstance(data.get('start_date'), str):
            self.start_date.setDate(QDate.fromString(data['start_date'], Qt.DateFormat.ISODate))
        elif isinstance(data.get('start_date'), datetime.date):
            self.start_date.setDate(data['start_date'])
            
        if isinstance(data.get('end_date'), str):
            self.end_date.setDate(QDate.fromString(data['end_date'], Qt.DateFormat.ISODate))
        elif isinstance(data.get('end_date'), datetime.date):
            self.end_date.setDate(data['end_date'])
            
        # Set Vehicles (Primary + Additional)
        self.assigned_vehicles = []
        
        # 1. Primary
        p_vid = data.get('vehicle_id')
        if p_vid:
            p_vehicle = {
                'vehicle_id': p_vid,
                'vehicle_name': data.get('vehicle_name', 'Unknown'),
                'driver_id': data.get('driver_id'),
                'driver_name': data.get('driver_name', 'Unknown'), # Can rely on hydration
                'override_cities': False, # Primary typically uses global
                'transit_periods': data.get('transit_periods', [])
            }
            self.assigned_vehicles.append(p_vehicle)
            
        # 2. Additional
        additional = data.get('additional_vehicles', [])
        for av in additional:
            # ensure keys
            if 'override_cities' not in av:
                av['override_cities'] = True if av.get('cities') else False
            self.assigned_vehicles.append(av)
            
        self.refresh_vehicle_table()
        
        # Set cities
        cities = data.get('cities', [])
        if not cities and data.get('city'):
            cities = [data['city']]
            
        for i in range(self.city_list.count()):
            item = self.city_list.item(i)
            city_name = item.data(Qt.ItemDataRole.UserRole)
            if city_name in cities:
                item.setSelected(True)
            else:
                item.setSelected(False)
                
        # Set per-city data
        self.city_periods = data.get('city_periods', {})
        self.city_schedules = data.get('city_schedules', {})
            
        # Handle Daily Hours (String <-> QTimeEdit)
        hours_str = data.get('daily_hours') or '09:00-17:00'
        try:
            if '-' in hours_str:
                start_str, end_str = hours_str.split('-')
                self.hours_start.setTime(QTime.fromString(start_str.strip(), "HH:mm"))
                self.hours_end.setTime(QTime.fromString(end_str.strip(), "HH:mm"))
            else:
                raise ValueError
        except:
            self.hours_start.setTime(QTime(9, 0))
            self.hours_end.setTime(QTime(17, 0))

        self.speed.setValue(data.get('vehicle_speed_kmh') or 25)
        self.stationing.setValue(data.get('stationing_min_per_hour') or 10)
        
        # Set Campaign Type (Exclusive vs Loop)
        is_excl = data.get('is_exclusive') or data.get('exclusive_mode')
        if is_excl:
            self.radio_exclusive.setChecked(True)
        else:
            self.radio_loop.setChecked(True)
            
        # Custom scheduleata.get('known_distance_total'):
        if data.get('known_distance_total'):
            self.use_known_distance.setChecked(True)
            self.distance_total.setValue(data.get('known_distance_total') or 0)
            
        self.spot_duration.setValue(data.get('spot_duration') or 10)
        self.loop_duration.setValue(data.get('loop_duration') or 60)
        
        # Custom schedule
        
        # Load financial data
        self.cost_per_km.setValue(data.get('cost_per_km') or 0)
        self.fixed_costs.setValue(data.get('fixed_costs') or 0)
        self.expected_revenue.setValue(data.get('expected_revenue') or 0)
        self.update_roi_display()
        
        self.pois_input.setText(data.get('pois') or '')
        self.route_data = data.get('route_data')
        if self.route_data:
            dist = self.route_data.get('distance_km', 0)
            self.distance_label.setText(f"Distance: {dist} km")
        
    def get_data(self):
        start_qdate = self.start_date.date()
        end_qdate = self.end_date.date()
        
        # Get selected cities
        selected_cities = []
        for i in range(self.city_list.count()):
            item = self.city_list.item(i)
            if item.isSelected():
                city_name = item.data(Qt.ItemDataRole.UserRole)
                selected_cities.append(city_name)
        
        # Get vehicle info (Multi-vehicle logic)
        primary_vehicle_data = {}
        additional_vehicles = []
        
        if self.assigned_vehicles:
            # First one is primary
            p = self.assigned_vehicles[0]
            primary_vehicle_data = {
                'vehicle_id': p['vehicle_id'],
                'vehicle_name': p.get('vehicle_name', ''), # Denormalized
                'driver_id': p.get('driver_id'),
                'driver_name': p.get('driver_name', ''),
                'transit_periods': p.get('transit_periods', [])
            }
            # Rest are additional
            for v in self.assigned_vehicles[1:]:
                additional_vehicles.append(v)
        else:
            # Should be blocked by validate_inputs, but fail safe
            primary_vehicle_data = {'vehicle_id': None, 'driver_id': None}

        # Serialize city_periods (convert dates to strings for JSON storage)
        serializable_periods = {}
        for city, periods in self.city_periods.items():
            if city == '__meta__':
                serializable_periods[city] = periods
                continue
                
            # Handle list of periods
            if isinstance(periods, list):
                s_periods = []
                for p in periods:
                    if isinstance(p, dict):
                        s_p = p.copy()
                        if isinstance(s_p.get('start'), datetime.date):
                            s_p['start'] = s_p['start'].isoformat()
                        if isinstance(s_p.get('end'), datetime.date):
                            s_p['end'] = s_p['end'].isoformat()
                        s_periods.append(s_p)
                serializable_periods[city] = s_periods
            # Handle legacy dict
            elif isinstance(periods, dict):
                s_p = periods.copy()
                if isinstance(s_p.get('start'), datetime.date):
                    s_p['start'] = s_p['start'].isoformat()
                if isinstance(s_p.get('end'), datetime.date):
                    s_p['end'] = s_p['end'].isoformat()
                serializable_periods[city] = s_p

        data = {
            'client_name': self.client_name.text(),
            'campaign_name': self.campaign_name.text(),
            'po_number': self.po_number.text(),
            'start_date': self.start_date.date().toPyDate(),
            'end_date': self.end_date.date().toPyDate(),
            'daily_hours': f"{self.hours_start.time().toString('HH:mm')}-{self.hours_end.time().toString('HH:mm')}",
            'cities': selected_cities,
            'city': selected_cities[0] if selected_cities else "", # Primary city for backward compat
            'vehicle_speed_kmh': self.speed.value(),
            'stationing_min_per_hour': self.stationing.value(),
            'is_exclusive': self.radio_exclusive.isChecked(),
            'status': self.status_combo.currentText().lower(), # SAVE STATUS
            
            # Vehicle Data (Primary)
            **primary_vehicle_data,
            'additional_vehicles': additional_vehicles, # New field
            
            # Financials
            'cost_per_km': self.cost_per_km.value(),
            'fixed_costs': self.fixed_costs.value(),
            'expected_revenue': self.expected_revenue.value(),
            
            # Spot Settings
            'spot_duration': self.spot_duration.value(),
            'loop_duration': self.loop_duration.value(),
            
            # POIs
            'pois': self.pois_input.toPlainText(),
            
            # Custom Schedule
            'custom_daily_schedule': self.custom_schedule,
            
            # Per-City Data
            'city_periods': serializable_periods,
            'city_schedules': self.city_schedules,
            
            # Custom Distance
            'known_distance_total': self.custom_distance_km
        }
        
        return data

    def toggle_loop_input(self, checked):
        """Disable loop duration if exclusive mode is on"""
        self.loop_duration.setEnabled(not checked)
    
    def toggle_distance_input(self, checked):
        """Enable/disable distance input fields"""
        self.distance_total.setEnabled(checked)
        # Custom daily distances are always available via button
    
    def set_custom_schedule(self):
        """Dialog to set custom daily schedule"""
        dialog = CustomScheduleDialog(self, self.start_date.date(), self.end_date.date())
        if dialog.exec():
            self.custom_daily_schedule = dialog.get_schedule()
            QMessageBox.information(
                self,
                "Orar Personalizat",
                f"Orar diferentiat setat pentru {len(self.custom_daily_schedule)} zile."
            )
    
    def set_custom_distances(self):
        """Dialog to set custom daily distances"""
        dialog = CustomDistanceDialog(self, self.start_date.date(), self.end_date.date())
        if dialog.exec():
            self.custom_daily_distances = dialog.get_distances()
            total_km = sum(self.custom_daily_distances.values())
            self.distance_daily_label.setText(f"{total_km:.1f} km total")
            self.distance_daily_label.setStyleSheet("color: #2196F3; font-weight: bold;")
            QMessageBox.information(
                self,
                "Distante Personalizate",
                f"Distante setate pentru {len(self.custom_daily_distances)} zile.\nTotal: {total_km:.1f} km"
            )
    
    def add_new_city(self):
        """Dialog to add a new city with population-based extrapolation"""
        from PyQt6.QtWidgets import QInputDialog
        
        # Get city name
        city_name, ok = QInputDialog.getText(
            self, 
            "Add New City",
            "Enter city name:"
        )
        
        if not ok or not city_name.strip():
            return
            
        city_name = city_name.strip()
        
        # Check if already exists
        if self.city_manager.get_city_profile(city_name):
            QMessageBox.warning(
                self,
                "City Exists",
                f"City '{city_name}' already exists in the database."
            )
            return
        
        # Get population
        population, ok = QInputDialog.getInt(
            self,
            "City Population",
            f"Enter population for {city_name}:\n(Data will be auto-extrapolated based on similar cities)",
            value=100000,
            min=1000,
            max=10000000
        )
        
        if not ok:
            return
        
        # Extrapolate data
        city_data = self.city_manager.extrapolate_city_data(city_name, population)
        
        if city_data:
            # Add to database
            self.city_manager.add_city(city_name, city_data)
            
            self.load_cities()
            # Select the new city
            items = self.city_list.findItems(city_name, Qt.MatchFlag.MatchStartsWith)
            if items:
                items[0].setSelected(True)
            
            QMessageBox.information(
                self,
                "City Added",
                f"City '{city_name}' added successfully with extrapolated data."
            )
        else:
            QMessageBox.critical(
                self,
                "Error",
                "Failed to extrapolate city data."
            )
    
    def load_cities(self):
        """Load cities into list widget"""
        self.city_list.clear()
        cities = self.city_manager.get_all_cities()
        
        for city in sorted(cities):
            # Get county info
            profile = self.city_manager.get_city_profile(city)
            county = ""
            if profile:
                # Try to find county in current or any period
                current_ref = profile.get('current', {}).get('ref')
                if current_ref and current_ref in profile:
                    county = profile[current_ref].get('county', '')
                else:
                    # Check first available period
                    for key, data in profile.items():
                        if key != 'current' and isinstance(data, dict):
                            county = data.get('county', '')
                            if county: break
            
            display_text = f"{city} ({county})" if county else city
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, city)
            self.city_list.addItem(item)
            
    def refresh_data(self):
        """Refresh data for selected cities with progress dialog and confirmation"""
        selected_items = self.city_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select at least one city to refresh.")
            return
            
        cities_to_refresh = []
        for item in selected_items:
            city = item.data(Qt.ItemDataRole.UserRole)
            if city:
                cities_to_refresh.append(city)
        
        # Create progress dialog
        progress = QProgressDialog("Fetching city data...", "Cancel", 0, len(cities_to_refresh), self)
        progress.setWindowTitle("Refreshing Data")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        
        success_count = 0
        failed_cities = []
        needs_confirmation = []
        
        for i, city in enumerate(cities_to_refresh):
            if progress.wasCanceled():
                break
                
            progress.setLabelText(f"Fetching data for {city}...")
            progress.setValue(i)
            QApplication.processEvents()
            
            # Refresh city data (respects preferences)
            result = self.city_manager.refresh_city_data(city)
            
            if result.get('success'):
                # Data fetched successfully
                success_count += 1
            elif result.get('needs_confirmation'):
                # Manual preference - needs user confirmation
                needs_confirmation.append(city)
            else:
                # Failed to fetch
                failed_cities.append(city)
        
        progress.setValue(len(cities_to_refresh))
        
        # Handle cities that need confirmation
        if needs_confirmation:
            for city in needs_confirmation:
                # Fetch new data with force=True to get it for comparison
                current_data = self.city_manager.get_city_profile(city)
                
                # Try to fetch new data
                result = self.city_manager.refresh_city_data(city, force=True)
                
                if result.get('success'):
                    new_data = result['data']
                    new_source = result['source']
                    
                    # Show confirmation dialog
                    dialog = CityUpdateConfirmationDialog(city, current_data, new_data, new_source, self)
                    
                    if dialog.exec():
                        # User accepted - data is already saved by refresh_city_data
                        success_count += 1
                    else:
                        # User rejected - revert to old data
                        if current_data:
                            self.city_manager.add_city(city, current_data)
                else:
                    failed_cities.append(city)
        
        # Show results
        if success_count > 0:
            self.load_cities()  # Reload city list to show updated data
            
        result_msg = f"Successfully refreshed {success_count}/{len(cities_to_refresh)} cities."
        if failed_cities:
            result_msg += f"\n\nFailed: {', '.join(failed_cities)}"
            
        QMessageBox.information(self, "Refresh Complete", result_msg)
    
    def open_update_preferences(self):
        """Open dialog to configure update preferences for cities"""
        dialog = CityUpdatePreferencesDialog(self.city_manager, self)
        dialog.exec()
        
        
    def import_kml(self):
        """Import KML file for route"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import KML Route", "", "KML Files (*.kml);;All Files (*)"
        )
        
        if not file_path:
            return
            
        result = parse_kml(file_path)
        
        if 'error' in result:
            QMessageBox.warning(self, "Import Error", f"Failed to parse KML: {result['error']}")
            return
            
        self.route_data = result
        
        # Update UI
        dist = result.get('distance_km', 0)
        self.distance_label.setText(f"Distance: {dist} km")
        
        # Auto-fill distance if not set
        if not self.use_known_distance.isChecked():
            self.use_known_distance.setChecked(True)
            self.distance_total.setValue(dist)
            
        QMessageBox.information(
            self, 
            "Route Imported", 
            f"Imported route '{result.get('name', 'Unknown')}'.\nDistance: {dist} km"
        )

    def center_on_screen(self):
        """Center the dialog on the screen"""
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.frameGeometry()
        center_point = screen.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())

    def update_source_label(self, city_name):
        """Update the source label based on selected city"""
        profile = self.city_manager.get_city_profile(city_name)
        if profile:
            source = profile.get('source', 'Local')
            updated = profile.get('last_updated', '')
            if updated:
                try:
                    dt = datetime.datetime.fromisoformat(updated)
                    updated = dt.strftime("%d %b %Y")
                except:
                    pass
                self.source_label.setText(f"Data: {source} ({updated})")
            else:
                self.source_label.setText(f"Data: {source}")
        else:
            self.source_label.setText("Data: New City (will extrapolate)")
    
    def export_campaign(self):
        """Export current campaign to JSON or CSV"""
        if not self.current_campaign_id:
            # Save first if not saved
            data = self.get_data()
            self.current_campaign_id = self.storage.save_campaign(data)
        
        # Ask for format
        format_choice = QMessageBox.question(
            self,
            "Export Format",
            "Choose export format:\\n\\nJSON (recommended) or CSV?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes
        )
        
        if format_choice == QMessageBox.StandardButton.Cancel:
            return
        
        is_json = format_choice == QMessageBox.StandardButton.Yes
        ext = "json" if is_json else "csv"
        filter_str = f"{ext.upper()} Files (*.{ext})"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Campaign",
            f"campaign_export.{ext}",
            filter_str
        )
        
        if file_path:
            if is_json:
                success = self.storage.export_to_json(self.current_campaign_id, file_path)
            else:
                success = self.storage.export_to_csv(self.current_campaign_id, file_path)
            
            if success:
                QMessageBox.information(self, "Success", f"Campaign exported to {file_path}")
            else:
                QMessageBox.critical(self, "Error", "Failed to export campaign")
    
    def import_campaign(self):
        """Import campaign from JSON or CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Campaign",
            "",
            "Campaign Files (*.json *.csv);;JSON Files (*.json);;CSV Files (*.csv)"
        )
        
        if not file_path:
            return
        
        # Determine format from extension
        is_json = file_path.lower().endswith('.json')
        
        if is_json:
            new_id = self.storage.import_from_json(file_path)
        else:
            new_id = self.storage.import_from_csv(file_path)
        
        if new_id:
            # Load the imported campaign
            campaign = self.storage.get_campaign(new_id)
            if campaign:
                self.load_campaign(campaign)
                QMessageBox.information(self, "Success", "Campaign imported successfully")
        else:
            QMessageBox.critical(self, "Error", "Failed to import campaign")
    
    def clone_current(self):
        """Clone the current campaign"""
        if not self.current_campaign_id:
            QMessageBox.warning(self, "No Campaign", "Please save the campaign first before cloning")
            return
        
        cloned_id = self.storage.clone_campaign(self.current_campaign_id)
        
        if cloned_id:
            # Load the cloned campaign
            campaign = self.storage.get_campaign(cloned_id)
            if campaign:
                self.load_campaign(campaign)
                QMessageBox.information(self, "Success", f"Campaign cloned successfully\\n\\nNew name: {campaign.get('campaign_name', '')}")
        else:
            QMessageBox.critical(self, "Error", "Failed to clone campaign")
    
    def update_roi_display(self):
        """Update ROI display based on current financial inputs"""
        # Calculate distance: manual first, then calculated
        distance = 0
        if self.use_known_distance.isChecked() and self.distance_total.value() > 0:
            # Use manual distance if set
            distance = self.distance_total.value()
        else:
            # Calculate from speed and hours
            try:
                start_qdate = self.start_date.date()
                end_qdate = self.end_date.date()
                campaign_days = (end_qdate.toPyDate() - start_qdate.toPyDate()).days + 1
                
                # Parse daily hours using QTime
                start_time = self.hours_start.time()
                end_time = self.hours_end.time()
                
                start_mins = start_time.hour() * 60 + start_time.minute()
                end_mins = end_time.hour() * 60 + end_time.minute()
                
                # Handle overnight (if end < start, add 24h)
                if end_mins < start_mins:
                    end_mins += 24 * 60
                    
                daily_hours = (end_mins - start_mins) / 60.0
                
                speed = self.speed.value()
                stationing = self.stationing.value()
                
                # Calculate effective driving time
                effective_hours = daily_hours - (daily_hours * stationing / 60)
                distance = effective_hours * speed * campaign_days
            except:
                distance = 0
        
        cost_km = self.cost_per_km.value()
        fixed = self.fixed_costs.value()
        revenue = self.expected_revenue.value()
        
        total_cost = (distance * cost_km) + fixed
        
        if total_cost > 0:
            roi = ((revenue - total_cost) / total_cost) * 100
            
            # Color code ROI
            if roi > 0:
                color = "#4CAF50"  # Green
                symbol = "+"
            elif roi < 0:
                color = "#F44336"  # Red
                symbol = ""
            self.roi_label.setStyleSheet(f"font-weight: bold; color: {color};")
        else:
            self.roi_label.setText("ROI: N/A (enter costs)")
            self.roi_label.setStyleSheet("font-weight: bold; color: #999;")
    
    def open_city_periods(self):
        """Open dialog to set periods per city"""
        # Validate global dates first
        if not self.start_date.date().isValid() or not self.end_date.date().isValid():
            QMessageBox.warning(self, "Invalid Dates", "Please set valid global start/end dates first.")
        start = self.start_date.date().toPyDate()
        end = self.end_date.date().toPyDate()
        
        # Get selected cities using UserRole to ensure raw matching
        from PyQt6.QtCore import Qt
        cities = []
        for i in range(self.city_list.count()):
            item = self.city_list.item(i)
            if item.isSelected():
                cities.append(item.data(Qt.ItemDataRole.UserRole))
        
        if not cities:
            QMessageBox.warning(self, "No Cities", "Please select at least one city first.")
            return
        
        # Build Vehicle Mapping for Dialog
        # Map: City -> List[Vehicle Name]
        city_vehicles = {}
        print(f"DEBUG: Assigned Vehicles: {self.assigned_vehicles}")
        for v in self.assigned_vehicles:
            v_name = v.get('vehicle_name', 'Unknown')
            d_name = v.get('driver_name', 'No Driver')
            display_str = f"{v_name} ({d_name})"
            
            # If vehicle has specific cities, map it there
            if v.get('override_cities'):
                print(f"DEBUG: Vehicle {v_name} has override cities: {v.get('cities')}")
                for c in v.get('cities', []):
                    # Check for strip/cleaning just in case
                    c_clean = c.strip()
                    if c_clean not in city_vehicles: city_vehicles[c_clean] = []
                    city_vehicles[c_clean].append(display_str)
            else:
                # If global, map to all selected global cities (conceptually)
                print(f"DEBUG: Vehicle {v_name} is GLOBAL. Mapping to {cities}")
                for c in cities:
                    if c not in city_vehicles: city_vehicles[c] = []
                    city_vehicles[c].append(f"{display_str} (Global)")
                    
        print(f"DEBUG: Final City Vehicles Map: {city_vehicles}")
        
        dialog = CityPeriodsDialog(cities, start, end, self.city_periods, self.city_schedules, parent=self)
        # Inject the mapping directly into dialog (hack since we didn't update constructor yet)
        dialog.city_vehicles_map = city_vehicles
        
        if dialog.exec():
            # Update periods data
            new_data = dialog.get_data()
            if '__meta__' in new_data:
                del new_data['__meta__'] # Don't store meta in periods dict if possible, or handle it
            
            self.city_periods = new_data
            
            # If dialog allows setting schedules too, get them
            if hasattr(dialog, 'city_schedules'):
                 self.city_schedules = dialog.get_schedules()
                 
            QMessageBox.information(self, "Success", "City periods updated.")

    def open_calendar(self):
        """Open calendar view to check availability"""
        dialog = CampaignCalendarView(self)
        dialog.exec()
        
    def generate_financial_report(self):
        """Generate dedicated financial PDF report"""
        if not self.current_campaign_id:
            QMessageBox.warning(self, "No Campaign", "Please save the campaign first")
            return
        
        # Get campaign data
        campaign_data = self.storage.get_campaign(self.current_campaign_id)
        if not campaign_data:
            QMessageBox.critical(self, "Error", "Campaign data not found")
            return
        
        # Check if financial data exists
        if campaign_data.get('cost_per_km', 0) == 0 and campaign_data.get('fixed_costs', 0) == 0:
            reply = QMessageBox.question(
                self,
                "No Financial Data",
                "No financial data entered. Generate report anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        # Calculate distance (same logic as campaign report)
        distance_km = 0
        if campaign_data.get('known_distance_total'):
            distance_km = campaign_data['known_distance_total']
        elif campaign_data.get('custom_daily_distances'):
            distance_km = sum(campaign_data['custom_daily_distances'].values())
        else:
            # Calculate from speed and hours
            try:
                start_date = datetime.date.fromisoformat(str(campaign_data.get('start_date')))
                end_date = datetime.date.fromisoformat(str(campaign_data.get('end_date')))
                campaign_days = (end_date - start_date).days + 1
                
                # Parse daily hours
                hours_str = campaign_data.get('daily_hours', '09:00-17:00')
                start_h, end_h = hours_str.split('-')
                start_mins = int(start_h.split(':')[0]) * 60 + int(start_h.split(':')[1])
                end_mins = int(end_h.split(':')[0]) * 60 + int(end_h.split(':')[1])
                daily_hours = (end_mins - start_mins) / 60
                
                speed = campaign_data.get('vehicle_speed_kmh', 25)
                stationing = campaign_data.get('stationing_min_per_hour', 15)
                
                # Calculate effective driving time
                effective_hours = daily_hours - (daily_hours * stationing / 60)
                distance_km = effective_hours * speed * campaign_days
            except:
                distance_km = 0
        
        # Add calculated distance to campaign data
        campaign_data_with_distance = campaign_data.copy()
        campaign_data_with_distance['calculated_distance'] = distance_km
        
        # Auto-generate filename (like campaign report)
        campaign_name = campaign_data.get('campaign_name', 'campaign')
        client_name = campaign_data.get('client_name', 'client')
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create reports directory if it doesn't exist
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        filename = f"financial_{client_name}_{campaign_name}_{timestamp}.pdf"
        file_path = os.path.join(reports_dir, filename)
        
        # Generate report
        try:
            from src.reporting.financial_report_generator import FinancialReportGenerator
            
            generator = FinancialReportGenerator()
            success = generator.generate_financial_report(campaign_data_with_distance, file_path)
            
            if success:
                # Open PDF automatically
                import subprocess
                import platform
                
                if platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', file_path])
                elif platform.system() == 'Windows':
                    os.startfile(file_path)
                else:  # Linux
                    subprocess.run(['xdg-open', file_path])
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Financial report generated and opened!\n\n{file_path}"
                )
            else:
                QMessageBox.critical(self, "Error", "Failed to generate financial report")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate financial report:\n\n{str(e)}")

    
    def optimize_route(self):
        """Optimize route based on traffic data"""
        try:
            # Get selected cities
            selected_cities = []
            city_data_list = []
            city_county_map = {}  # Store city -> county mapping
            
            for i in range(self.city_list.count()):
                item = self.city_list.item(i)
                if item.isSelected():
                    city_text = item.text()
                    city_name = city_text.split(' (')[0] if ' (' in city_text else city_text
                    county = city_text.split('(')[1].rstrip(')') if '(' in city_text else 'Unknown'
                    selected_cities.append(city_name)
                    city_county_map[city_name] = county
            
            if len(selected_cities) == 0:
                QMessageBox.warning(self, "No Selection", "Please select at least one city.")
                return
            
            # --- Intra-City Optimization (Single City) ---
            if len(selected_cities) == 1:
                city_name = selected_cities[0]
                user_pois_text = self.pois_input.toPlainText()
                user_pois = [p.strip() for p in user_pois_text.split('\n') if p.strip()]
                
                if not user_pois:
                    QMessageBox.warning(
                        self, 
                        "No POIs", 
                        f"To optimize route within {city_name}, please enter some POIs (Points of Interest) in the 'Route Data' tab first."
                    )
                    return
                
                from src.utils.route_optimizer import RouteOptimizer
                optimizer = RouteOptimizer()
                
                optimized_route, score = optimizer.suggest_city_route(city_name, user_pois)
                
                result_text = f"**Optimized City Route: {city_name}**\n"
                result_text += f"Traffic Score: {score:.1f}\n\n"
                result_text += "Suggested Path:\n"
                for i, point in enumerate(optimized_route, 1):
                    result_text += f"{i}. {point}\n"
                
                reply = QMessageBox.question(
                    self,
                    "City Route Optimization",
                    result_text + "\n\nAppend this route to your POIs list?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    current_text = self.pois_input.toPlainText()
                    new_text = current_text + "\n\n--- Optimized Route ---\n" + "\n".join(optimized_route)
                    self.pois_input.setText(new_text)
                    QMessageBox.information(self, "Success", "Route added to POIs!")
                return

            # --- Inter-City Optimization (Multiple Cities) ---
            if len(selected_cities) < 2:
                # Should be covered by single city logic, but safety check
                return
            
            # Get city data from manager
            from src.data.city_data_manager import CityDataManager
            manager = CityDataManager()
            
            for city_name in selected_cities:
                city_profile = manager.get_city_profile(city_name)
                if city_profile:
                    # city_profile is already the data for the period, not a nested structure
                    # Add city name and county to the data
                    city_profile['name'] = city_name
                    city_profile['county'] = city_county_map.get(city_name, 'Unknown')
                    city_data_list.append(city_profile)
            
            if not city_data_list:
                QMessageBox.critical(self, "Error", "Could not load city data")
                return
            
            # Optimize route
            from src.utils.route_optimizer import RouteOptimizer
            optimizer = RouteOptimizer()
            
            optimized_route, total_score = optimizer.suggest_optimal_route(city_data_list)
            route_details = optimizer.calculate_route_score(city_data_list)
            
            # Show results
            result_text = f"Optimized Route (Score: {total_score:.1f})\n\n"
            result_text += " → ".join(optimized_route) + "\n\n"
            result_text += "City Breakdown:\n"
            
            for city in route_details['breakdown']:
                result_text += f"• {city['city']}: {city['score']:.1f} points\n"
                result_text += f"  Population: {city['population']:,} | Traffic: {city['traffic']:,}\n"
            
            result_text += f"\nAverage Score: {route_details['average_score']:.1f}"
            
            # Update city list order
            reply = QMessageBox.question(
                self,
                "Route Optimization Results",
                result_text + "\n\nApply this optimized route order?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Reorder cities in the list
                self.city_list.clear()
                for city_name in optimized_route:
                    county = city_county_map.get(city_name, 'Unknown')
                    self.city_list.addItem(f"{city_name} ({county})")
                
                # Select all cities
                for i in range(self.city_list.count()):
                    self.city_list.item(i).setSelected(True)
                
                QMessageBox.information(self, "Success", "Route optimized and applied!")
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            QMessageBox.critical(
                self, 
                "Optimization Error", 
                f"Failed to optimize route:\n\n{str(e)}\n\nDetails:\n{error_details}"
            )



    
