from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QLabel, QDialogButtonBox, QComboBox, QWidget, QCheckBox, QGroupBox)
from PyQt6.QtCore import Qt

class CityUpdatePreferencesDialog(QDialog):
    """Dialog to manage update preferences for cities"""
    
    def __init__(self, city_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("City Update Preferences")
        self.resize(700, 600)
        
        self.city_manager = city_manager
        self.preference_combos = {}  # Store combo boxes by city name
        self.city_checkboxes = {}    # Store checkboxes by city name
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Info label
        info_label = QLabel(
            "<b>Update Preferences</b><br>"
            "Choose how each city's data should be updated:<br>"
            "• <b>Public</b>: Automatic updates from public sources<br>"
            "• <b>INS</b>: Use INS API when available (fallback to Public)<br>"
            "• <b>BRAT</b>: Use BRAT API when available (fallback to Public)<br>"
            "• <b>Manual</b>: Only update with your confirmation"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        layout.addWidget(info_label)
        
        # Bulk Actions
        bulk_group = QGroupBox("Bulk Actions")
        bulk_layout = QHBoxLayout()
        
        self.select_all_cb = QCheckBox("Select All")
        self.select_all_cb.stateChanged.connect(self.toggle_select_all)
        bulk_layout.addWidget(self.select_all_cb)
        
        bulk_layout.addStretch()
        
        bulk_layout.addWidget(QLabel("Change selected to:"))
        
        self.bulk_combo = QComboBox()
        self.bulk_combo.addItems(["Public", "INS", "BRAT", "Manual"])
        bulk_layout.addWidget(self.bulk_combo)
        
        apply_btn = QPushButton("Apply to Selected")
        apply_btn.clicked.connect(self.apply_bulk_change)
        bulk_layout.addWidget(apply_btn)
        
        bulk_group.setLayout(bulk_layout)
        layout.addWidget(bulk_group)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Select", "City", "Update Preference"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        # Populate cities
        self.populate_cities()
        
        layout.addWidget(self.table)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save_preferences)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def populate_cities(self):
        """Populate table with all cities and their preferences"""
        cities = self.city_manager.get_all_cities()
        self.table.setRowCount(0)
        self.preference_combos = {}
        self.city_checkboxes = {}
        
        for row, city in enumerate(sorted(cities)):
            self.table.insertRow(row)
            
            # Checkbox
            checkbox = QCheckBox()
            # Center checkbox
            cell_widget = QWidget()
            layout_cb = QHBoxLayout(cell_widget)
            layout_cb.addWidget(checkbox)
            layout_cb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout_cb.setContentsMargins(0, 0, 0, 0)
            
            self.table.setCellWidget(row, 0, cell_widget)
            self.city_checkboxes[city] = checkbox
            
            # City name
            self.table.setItem(row, 1, QTableWidgetItem(city))
            
            # Preference combo box
            combo = QComboBox()
            combo.addItems(["Public", "INS", "BRAT", "Manual"])
            
            # Set current preference
            current_pref = self.city_manager.get_update_preference(city)
            pref_map = {'public': 0, 'ins': 1, 'brat': 2, 'manual': 3}
            combo.setCurrentIndex(pref_map.get(current_pref, 0))
            
            self.table.setCellWidget(row, 2, combo)
            self.preference_combos[city] = combo
            
    def toggle_select_all(self, state):
        """Select or deselect all cities"""
        checked = state == Qt.CheckState.Checked.value
        for checkbox in self.city_checkboxes.values():
            checkbox.setChecked(checked)
            
    def apply_bulk_change(self):
        """Apply selected bulk preference"""
        target_idx = self.bulk_combo.currentIndex()
        
        count = 0
        for city, checkbox in self.city_checkboxes.items():
            if checkbox.isChecked():
                if city in self.preference_combos:
                    self.preference_combos[city].setCurrentIndex(target_idx)
                    count += 1
                    
        # Optional: feedback could be shown here, but visual update is usually enough
            
    def save_preferences(self):
        """Save all preferences and close"""
        pref_map = {0: 'public', 1: 'ins', 2: 'brat', 3: 'manual'}
        
        for city, combo in self.preference_combos.items():
            preference = pref_map[combo.currentIndex()]
            self.city_manager.set_update_preference(city, preference)
        
        self.accept()
