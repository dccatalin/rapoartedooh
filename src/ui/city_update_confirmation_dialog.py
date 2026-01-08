"""
City Update Confirmation Dialog
Shows comparison between current and new city data before applying updates.
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QLabel, QDialogButtonBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

class CityUpdateConfirmationDialog(QDialog):
    """Dialog to confirm city data updates by showing old vs new comparison"""
    
    def __init__(self, city_name, current_data, new_data, new_source, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Confirm Update: {city_name}")
        self.resize(700, 500)
        
        self.city_name = city_name
        self.current_data = current_data or {}
        self.new_data = new_data or {}
        self.new_source = new_source
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Info label
        current_source = self.current_data.get('source', 'Unknown')
        info_text = f"<b>{self.city_name}</b><br>"
        info_text += f"Current Source: <i>{current_source}</i><br>"
        info_text += f"New Source: <i>{self.new_source}</i>"
        
        info_label = QLabel(info_text)
        info_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        layout.addWidget(info_label)
        
        # Comparison table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Field", "Current Value", "New Value"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        # Populate comparison
        self.populate_comparison()
        
        layout.addWidget(self.table)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Apply Update")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Keep Current")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def populate_comparison(self):
        """Populate table with field comparisons"""
        # Define fields to compare
        fields = {
            'population': 'Population',
            'daily_traffic_total': 'Daily Traffic',
            'daily_pedestrian_total': 'Daily Pedestrians',
            'active_population_pct': 'Active Population %',
            'avg_commute_distance_km': 'Avg Commute Distance (km)',
            'last_updated': 'Last Updated'
        }
        
        row = 0
        for key, label in fields.items():
            current_val = self.current_data.get(key, 'N/A')
            new_val = self.new_data.get(key, 'N/A')
            
            # Format values
            if isinstance(current_val, (int, float)) and key != 'last_updated':
                current_val = f"{current_val:,}"
            if isinstance(new_val, (int, float)) and key != 'last_updated':
                new_val = f"{new_val:,}"
            
            # Truncate timestamps
            if key == 'last_updated':
                if isinstance(current_val, str) and len(current_val) > 10:
                    current_val = current_val[:10]
                if isinstance(new_val, str) and len(new_val) > 10:
                    new_val = new_val[:10]
            
            self.table.insertRow(row)
            
            # Field name
            self.table.setItem(row, 0, QTableWidgetItem(label))
            
            # Current value
            current_item = QTableWidgetItem(str(current_val))
            self.table.setItem(row, 1, current_item)
            
            # New value
            new_item = QTableWidgetItem(str(new_val))
            
            # Highlight if different
            if str(current_val) != str(new_val):
                new_item.setBackground(QColor(255, 255, 200))  # Light yellow
            
            self.table.setItem(row, 2, new_item)
            
            row += 1
