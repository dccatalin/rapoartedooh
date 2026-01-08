from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
                               QTableWidget, QTableWidgetItem, QPushButton, QMessageBox,
                               QHeaderView, QInputDialog, QFormLayout, QLineEdit, QSpinBox,
                               QDoubleSpinBox, QLabel, QComboBox, QDateEdit, QDialogButtonBox,
                               QListWidget, QGroupBox, QTextEdit, QProgressDialog, QApplication)
from PyQt6.QtCore import QDate, Qt
import json
import os
import datetime
from src.ui.city_update_confirmation_dialog import CityUpdateConfirmationDialog
from src.ui.city_update_preferences_dialog import CityUpdatePreferencesDialog

class CityManagerDialog(QDialog):
    """Comprehensive dialog for managing cities, demographics, and events"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Cities & Events")
        self.resize(900, 600)
        
        # Paths
        self.cities_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'city_data_history.json')
        self.events_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'special_events.json')
        
        # Load data
        self.cities_data = self._load_json(self.cities_path)
        self.events_data = self._load_json(self.events_path)
        
        # Initialize CityDataManager for refresh operations
        from src.data.city_data_manager import CityDataManager
        self.city_manager = CityDataManager()
        
        self.current_city = None
        
        self.init_ui()
        self.load_cities()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Top section with city list and tabs
        top_layout = QHBoxLayout()
        
        # Left panel - City list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        left_layout.addWidget(QLabel("Cities:"))
        
        self.city_list = QListWidget()
        self.city_list.currentTextChanged.connect(self.on_city_selected)
        left_layout.addWidget(self.city_list)
        
        # City management buttons
        city_btn_layout = QVBoxLayout() # Changed to VBox for better organization
        
        add_city_btn = QPushButton("Add City")
        add_city_btn.clicked.connect(self.add_city)
        city_btn_layout.addWidget(add_city_btn)
        
        delete_city_btn = QPushButton("Delete City")
        delete_city_btn.clicked.connect(self.delete_city)
        city_btn_layout.addWidget(delete_city_btn)
        
        # Separator
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #ccc;")
        city_btn_layout.addWidget(line)
        
        # New Buttons
        refresh_btn = QPushButton("Refresh Data")
        refresh_btn.setToolTip("Update city data from external sources")
        refresh_btn.clicked.connect(self.refresh_data)
        city_btn_layout.addWidget(refresh_btn)
        
        prefs_btn = QPushButton("Update Preferences")
        prefs_btn.setToolTip("Configure how each city's data is updated")
        prefs_btn.clicked.connect(self.open_update_preferences)
        city_btn_layout.addWidget(prefs_btn)
        
        left_layout.addLayout(city_btn_layout)
        
        left_panel.setMaximumWidth(200)
        top_layout.addWidget(left_panel)
        
        # Right panel - Tabs
        self.tabs = QTabWidget()
        
        # Demographics tab
        self.demo_tab = self.create_demographics_tab()
        self.tabs.addTab(self.demo_tab, "Demographics")
        
        # Events tab
        self.events_tab = self.create_events_tab()
        self.tabs.addTab(self.events_tab, "Special Events")
        
        top_layout.addWidget(self.tabs)
        
        main_layout.addLayout(top_layout)
        
        # Bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        save_btn = QPushButton("Save All Changes")
        save_btn.clicked.connect(self.save_all)
        save_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px 16px;")
        bottom_layout.addWidget(save_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(close_btn)
        
        main_layout.addLayout(bottom_layout)
        
    def create_demographics_tab(self):
        """Create demographics editing tab"""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # Population
        self.pop_input = QSpinBox()
        self.pop_input.setRange(1000, 10000000)
        self.pop_input.setSingleStep(1000)
        layout.addRow("Population:", self.pop_input)
        
        # County
        self.county_input = QLineEdit()
        self.county_input.setPlaceholderText("e.g., Ilfov, Cluj, Brasov")
        layout.addRow("County (Judet):", self.county_input)
        
        # Active population %
        self.active_pop_input = QSpinBox()
        self.active_pop_input.setRange(1, 100)
        self.active_pop_input.setSuffix("%")
        layout.addRow("Active Population %:", self.active_pop_input)
        
        # Daily traffic
        self.traffic_input = QSpinBox()
        self.traffic_input.setRange(0, 10000000)
        self.traffic_input.setSingleStep(1000)
        layout.addRow("Daily Traffic (vehicles):", self.traffic_input)
        
        # Daily pedestrian
        self.pedestrian_input = QSpinBox()
        self.pedestrian_input.setRange(0, 10000000)
        self.pedestrian_input.setSingleStep(1000)
        layout.addRow("Daily Pedestrian:", self.pedestrian_input)
        
        # Modal split
        modal_group = QGroupBox("Modal Split (%)")
        modal_layout = QFormLayout()
        
        self.auto_input = QSpinBox()
        self.auto_input.setRange(0, 100)
        self.auto_input.setSuffix("%")
        modal_layout.addRow("Auto:", self.auto_input)
        
        self.walking_input = QSpinBox()
        self.walking_input.setRange(0, 100)
        self.walking_input.setSuffix("%")
        modal_layout.addRow("Walking:", self.walking_input)
        
        self.cycling_input = QSpinBox()
        self.cycling_input.setRange(0, 100)
        self.cycling_input.setSuffix("%")
        modal_layout.addRow("Cycling:", self.cycling_input)
        
        self.public_transport_input = QSpinBox()
        self.public_transport_input.setRange(0, 100)
        self.public_transport_input.setSuffix("%")
        modal_layout.addRow("Public Transport:", self.public_transport_input)
        
        modal_group.setLayout(modal_layout)
        layout.addRow(modal_group)
        
        # Avg commute distance
        self.commute_input = QSpinBox()
        self.commute_input.setRange(1, 100)
        self.commute_input.setSuffix(" km")
        layout.addRow("Avg Commute Distance:", self.commute_input)
        
        # Description
        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(80)
        layout.addRow("Description:", self.desc_input)
        
        # Update button
        update_btn = QPushButton("Update Demographics")
        update_btn.clicked.connect(self.update_demographics)
        layout.addRow("", update_btn)
        
        return tab
        
    def create_events_tab(self):
        """Create events management tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Events table
        self.events_table = QTableWidget()
        self.events_table.setColumnCount(4)
        self.events_table.setHorizontalHeaderLabels(["Date", "Event Name", "Traffic Mult", "Pedestrian Mult"])
        self.events_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.events_table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        add_event_btn = QPushButton("Add Event")
        add_event_btn.clicked.connect(self.add_event)
        btn_layout.addWidget(add_event_btn)
        
        edit_event_btn = QPushButton("Edit Event")
        edit_event_btn.clicked.connect(self.edit_event)
        btn_layout.addWidget(edit_event_btn)
        
        delete_event_btn = QPushButton("Delete Event")
        delete_event_btn.clicked.connect(self.delete_event)
        btn_layout.addWidget(delete_event_btn)
        
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        return tab
        
    def _load_json(self, path):
        """Load JSON file"""
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
            
    def _save_json(self, path, data):
        """Save JSON file"""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")
            return False
            
    def load_cities(self):
        """Load cities into list"""
        # Reload fresh data
        self.cities_data = self._load_json(self.cities_path)
        
        self.city_list.clear()
        for city in sorted(self.cities_data.keys()):
            # Get county info if available
            city_data = self.cities_data[city]
            current_ref = city_data.get('current', {}).get('ref')
            county = ""
            if current_ref and current_ref in city_data:
                county = city_data[current_ref].get('county', '')
            
            display_text = f"{city} ({county})" if county else city
            self.city_list.addItem(display_text)
            
    def on_city_selected(self, current_text):
        """Handle city selection"""
        if not current_text:
            return
            
        # Extract city name from "City (County)" format
        city_name = current_text.split(' (')[0] if ' (' in current_text else current_text
        
        if city_name not in self.cities_data:
            return
            
        self.current_city = city_name
        self.load_city_demographics(city_name)
        self.load_city_events(city_name)
        
    def load_city_demographics(self, city_name):
        """Load city demographics into form"""
        city_data = self.cities_data[city_name]
        
        # Get current period data
        current_ref = city_data.get('current', {}).get('ref')
        if current_ref and current_ref in city_data:
            data = city_data[current_ref]
        else:
            # Get first non-current key
            data = next((v for k, v in city_data.items() if k != 'current'), {})
            
        self.pop_input.setValue(data.get('population', 100000))
        self.county_input.setText(data.get('county', ''))
        self.active_pop_input.setValue(data.get('active_population_pct', 60))
        self.traffic_input.setValue(data.get('daily_traffic_total', 50000))
        self.pedestrian_input.setValue(data.get('daily_pedestrian_total', 50000))
        
        modal_split = data.get('modal_split', {})
        self.auto_input.setValue(modal_split.get('auto', 35))
        self.walking_input.setValue(modal_split.get('walking', 27))
        self.cycling_input.setValue(modal_split.get('cycling', 4))
        self.public_transport_input.setValue(modal_split.get('public_transport', 34))
        
        self.commute_input.setValue(data.get('avg_commute_distance_km', 8))
        self.desc_input.setPlainText(data.get('description', ''))
        
    def load_city_events(self, city_name):
        """Load city events into table"""
        self.events_table.setRowCount(0)
        
        if city_name not in self.events_data:
            return
            
        city_events = self.events_data[city_name]
        for date_str, event_data in sorted(city_events.items()):
            row = self.events_table.rowCount()
            self.events_table.insertRow(row)
            
            self.events_table.setItem(row, 0, QTableWidgetItem(date_str))
            self.events_table.setItem(row, 1, QTableWidgetItem(event_data.get('name', '')))
            self.events_table.setItem(row, 2, QTableWidgetItem(str(event_data.get('traffic_multiplier', 1.0))))
            self.events_table.setItem(row, 3, QTableWidgetItem(str(event_data.get('pedestrian_multiplier', 1.0))))
            
    def add_city(self):
        """Add new city with update preference prompt"""
        # Create dialog to ask for name AND preference
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New City")
        form = QFormLayout(dialog)
        
        name_input = QLineEdit()
        form.addRow("City Name:", name_input)
        
        pref_combo = QComboBox()
        pref_combo.addItems(["Public (Auto)", "INS (API)", "BRAT (API)", "Manual (No Auto-Update)"])
        form.addRow("Update Preference:", pref_combo)
        
        pop_input = QSpinBox()
        pop_input.setRange(1000, 10000000)
        pop_input.setValue(100000)
        pop_input.setSingleStep(1000)
        form.addRow("Population (est.):", pop_input)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        form.addRow(btns)
        
        if dialog.exec():
            city_name = name_input.text().strip()
            if not city_name:
                return
            
            if city_name in self.cities_data:
                QMessageBox.warning(self, "City Exists", f"City '{city_name}' already exists.")
                return
                
            population = pop_input.value()
            preference_idx = pref_combo.currentIndex()
            # Map index to preference string
            pref_map = {0: 'public', 1: 'ins', 2: 'brat', 3: 'manual'}
            preference = pref_map.get(preference_idx, 'public')
            
            # Save preference immediately
            self.city_manager.set_update_preference(city_name, preference)
            
            # Create default data
            now = datetime.datetime.now()
            quarter = (now.month - 1) // 3 + 1
            period_key = f"{now.year}-Q{quarter}"
            
            self.cities_data[city_name] = {
                period_key: {
                    'population': population,
                    'county': '',
                    'active_population_pct': 60,
                    'daily_traffic_total': int(population * 0.5),
                    'daily_pedestrian_total': int(population * 0.6),
                    'modal_split': {
                        'auto': 35,
                        'walking': 27,
                        'cycling': 4,
                        'public_transport': 34
                    },
                    'avg_commute_distance_km': 8,
                    'description': f'City with population {population:,}',
                    'source': 'User Input',
                    'last_updated': now.isoformat()
                },
                'current': {'ref': period_key}
            }
            
            # Save immediately to ensure persistence
            self._save_json(self.cities_path, self.cities_data)
            
            self.load_cities()
            # Select new city
            items = self.city_list.findItems(city_name, Qt.MatchFlag.MatchStartsWith)
            if items:
                self.city_list.setCurrentItem(items[0])
            
    def delete_city(self):
        """Delete selected city"""
        if not self.current_city:
            QMessageBox.warning(self, "No Selection", "Please select a city to delete.")
            return
            
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete city '{self.current_city}' and all its data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.cities_data[self.current_city]
            if self.current_city in self.events_data:
                del self.events_data[self.current_city]
                
            # Need to save immediately
            self._save_json(self.cities_path, self.cities_data)
            self._save_json(self.events_path, self.events_data)
            
            self.current_city = None
            self.load_cities()
            
    def update_demographics(self):
        """Update demographics for current city"""
        if not self.current_city:
            QMessageBox.warning(self, "No City", "Please select a city first.")
            return
            
        # Get current period
        city_data = self.cities_data[self.current_city]
        current_ref = city_data.get('current', {}).get('ref')
        
        if not current_ref:
            # Create new period
            now = datetime.datetime.now()
            quarter = (now.month - 1) // 3 + 1
            current_ref = f"{now.year}-Q{quarter}"
            city_data['current'] = {'ref': current_ref}
            
        # Update data
        city_data[current_ref] = {
            'population': self.pop_input.value(),
            'county': self.county_input.text(),
            'active_population_pct': self.active_pop_input.value(),
            'daily_traffic_total': self.traffic_input.value(),
            'daily_pedestrian_total': self.pedestrian_input.value(),
            'modal_split': {
                'auto': self.auto_input.value(),
                'walking': self.walking_input.value(),
                'cycling': self.cycling_input.value(),
                'public_transport': self.public_transport_input.value()
            },
            'avg_commute_distance_km': self.commute_input.value(),
            'description': self.desc_input.toPlainText(),
            'source': 'User Input',
            'last_updated': datetime.datetime.now().isoformat()
        }
        
        # Save updates
        self._save_json(self.cities_path, self.cities_data)
        
        QMessageBox.information(self, "Success", f"Demographics updated for {self.current_city}")
        
        # Refresh list and re-select to update UI
        self.load_cities()
        items = self.city_list.findItems(self.current_city, Qt.MatchFlag.MatchStartsWith)
        if items:
            self.city_list.setCurrentItem(items[0])
            
    def add_event(self):
        """Add event for current city"""
        if not self.current_city:
            QMessageBox.warning(self, "No City", "Please select a city first.")
            return
            
        from src.ui.events_manager_dialog import EventEditorDialog
        dialog = EventEditorDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            event_key = data['start_date']
            
            if self.current_city not in self.events_data:
                self.events_data[self.current_city] = {}
                
            self.events_data[self.current_city][event_key] = data
            self._save_json(self.events_path, self.events_data)
            
            self.load_city_events(self.current_city)
            
    def edit_event(self):
        """Edit selected event"""
        row = self.events_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an event to edit.")
            return
            
        if not self.current_city:
            return
            
        # Find event key
        event_key = None
        current_row = 0
        for key in sorted(self.events_data[self.current_city].keys()):
            if current_row == row:
                event_key = key
                break
            current_row += 1
        
        if not event_key:
            return
            
        event_data = self.events_data[self.current_city][event_key]
        
        from src.ui.events_manager_dialog import EventEditorDialog
        dialog = EventEditorDialog(self, self.current_city, event_key, event_data)
        if dialog.exec():
            data = dialog.get_data()
            new_key = data['start_date']
            
            if new_key != event_key:
                del self.events_data[self.current_city][event_key]
                
            self.events_data[self.current_city][new_key] = data
            self._save_json(self.events_path, self.events_data)
            
            self.load_city_events(self.current_city)
            
    def delete_event(self):
        """Delete selected event"""
        row = self.events_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an event to delete.")
            return
            
        if not self.current_city:
            return
            
        date_str = self.events_table.item(row, 0).text()
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete event on {date_str}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.events_data[self.current_city][date_str]
            self._save_json(self.events_path, self.events_data)
            self.load_city_events(self.current_city)
            
    def save_all(self):
        """Save all changes"""
        # Data is already saved incrementally, but keep this for manual backup trigger if needed
        if self._save_json(self.cities_path, self.cities_data) and \
           self._save_json(self.events_path, self.events_data):
            QMessageBox.information(self, "Success", "All changes saved successfully!")
            self.accept()

    def refresh_data(self):
        """Refresh data for selected city"""
        # In this dialog context, we can select from the list
        selected_items = self.city_list.selectedItems()
        if not selected_items:
            if self.current_city:
                # Add current city as selection
                pass
            else:
                QMessageBox.warning(self, "No Selection", "Please select a city to refresh.")
                return
        
        if self.current_city:
            cities_to_refresh = [self.current_city]
        elif selected_items:
            cities_to_refresh = []
            for item in selected_items:
                city_str = item.text()
                # Parse city name again
                city = city_str.split(' (')[0] if ' (' in city_str else city_str
                cities_to_refresh.append(city)
        else:
            return

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
            
            result = self.city_manager.refresh_city_data(city)
            
            if result.get('success'):
                success_count += 1
            elif result.get('needs_confirmation'):
                needs_confirmation.append(city)
            else:
                failed_cities.append(city)
        
        progress.setValue(len(cities_to_refresh))
        
        if needs_confirmation:
            for city in needs_confirmation:
                current_data = self.city_manager.get_city_profile(city)
                result = self.city_manager.refresh_city_data(city, force=True)
                
                if result.get('success'):
                    new_data = result['data']
                    new_source = result['source']
                    
                    dialog = CityUpdateConfirmationDialog(city, current_data, new_data, new_source, self)
                    if dialog.exec():
                        success_count += 1
                    else:
                        if current_data:
                            self.city_manager.add_city(city, current_data)
                else:
                    failed_cities.append(city)
        
        if success_count > 0:
            self.load_cities()
            # Re-select current city to update inputs
            if self.current_city:
                 items = self.city_list.findItems(self.current_city, Qt.MatchFlag.MatchStartsWith)
                 if items:
                     self.city_list.setCurrentItem(items[0])
            
        result_msg = f"Successfully refreshed {success_count}/{len(cities_to_refresh)} cities."
        if failed_cities:
            result_msg += f"\\n\\nFailed: {', '.join(failed_cities)}"
            
        QMessageBox.information(self, "Refresh Complete", result_msg)

    def open_update_preferences(self):
        """Open update preferences dialog"""
        dialog = CityUpdatePreferencesDialog(self.city_manager, self)
        dialog.exec()
