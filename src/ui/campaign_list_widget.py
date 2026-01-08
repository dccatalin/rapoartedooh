from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QTableWidget, QTableWidgetItem, QHeaderView, 
                               QLabel, QLineEdit, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
from src.data.campaign_storage import CampaignStorage

class CampaignListWidget(QWidget):
    """
    Reusable widget for listing campaigns with search and refresh capabilities.
    """
    campaign_double_clicked = pyqtSignal(str) # Emits campaign_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.storage = CampaignStorage()
        self.campaigns = []
        self.init_ui()
        self.load_campaigns()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Top Bar (Search & Refresh) ---
        top_bar = QHBoxLayout()
        
        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search campaigns...")
        self.search_input.textChanged.connect(self.filter_campaigns)
        top_bar.addWidget(self.search_input)
        
        # Refresh
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_campaigns)
        top_bar.addWidget(refresh_btn)
        
        layout.addLayout(top_bar)
        
        # --- Table View ---
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Status", "Campaign Name", "Client", "Vehicle / Driver", "Period", "ID"
        ])
        
        # Table settings
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setColumnHidden(5, True) # Hide ID column
        
        # Events
        self.table.doubleClicked.connect(self.on_double_click)
        
        layout.addWidget(self.table)
        
        # Record count
        self.count_label = QLabel("0 campaigns")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.count_label)
        
    def load_campaigns(self):
        """Load all campaigns from storage"""
        self.campaigns = self.storage.get_all_campaigns()
        self.populate_table(self.campaigns)
        
    def populate_table(self, campaigns):
        """Populate table with campaign list"""
        self.table.setRowCount(len(campaigns))
        self.table.setSortingEnabled(False) # Disable sorting while inserting
        
        for i, camp in enumerate(campaigns):
            # 1. Status
            status = (camp.get('status') or 'unknown').capitalize()
            item_status = QTableWidgetItem(status)
            if status == 'Confirmed':
                item_status.setForeground(QBrush(QColor("green")))
            elif status == 'Canceled':
                item_status.setForeground(QBrush(QColor("red")))
            self.table.setItem(i, 0, item_status)
            
            # 2. Name
            item_name = QTableWidgetItem(camp.get('campaign_name', ''))
            self.table.setItem(i, 1, item_name)
            
            # 3. Client
            item_client = QTableWidgetItem(camp.get('client_name', ''))
            self.table.setItem(i, 2, item_client)
            
            # 4. Vehicle / Driver
            veh_name = camp.get('vehicle_name', 'N/A')
            driver = camp.get('driver_name')
            
            # Logic: If driver is missing or "N/A", just show vehicle.
            # If driver exists and is not N/A, show "Vehicle (Driver)"
            if driver and driver != "N/A":
                veh_str = f"{veh_name} ({driver})"
            else:
                veh_str = veh_name
                
            # Check for additional vehicles
            add_vehs = camp.get('additional_vehicles', [])
            if add_vehs:
                veh_str += f" (+{len(add_vehs)})"
                
            self.table.setItem(i, 3, QTableWidgetItem(veh_str))
            
            # 5. Period
            start = camp.get('start_date')
            end = camp.get('end_date')
            period_str = f"{start} to {end}"
            self.table.setItem(i, 4, QTableWidgetItem(period_str))
            
            # 6. ID (Hidden, but accessible)
            item_id = QTableWidgetItem(camp.get('id'))
            self.table.setItem(i, 5, item_id)
            
        self.table.setSortingEnabled(True)
        self.count_label.setText(f"{len(campaigns)} campaigns")
        
    def filter_campaigns(self, text):
        """Filter table rows based on text"""
        text = text.lower()
        filtered = []
        for camp in self.campaigns:
            # Search in name, client, vehicle
            if (text in camp.get('campaign_name', '').lower() or
                text in camp.get('client_name', '').lower() or
                text in camp.get('vehicle_name', '').lower()):
                filtered.append(camp)
        
        self.populate_table(filtered)
        
    def get_selected_campaign_id(self):
        """Get ID of currently selected campaign"""
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        
        row = rows[0].row()
        item = self.table.item(row, 5) # ID column
        return item.text() if item else None
        
    def on_double_click(self):
        """Handle double click event"""
        camp_id = self.get_selected_campaign_id()
        if camp_id:
            self.campaign_double_clicked.emit(camp_id)
