from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton)
from src.ui.campaign_list_widget import CampaignListWidget

class CampaignSelectionDialog(QDialog):
    """
    Dialog to select a campaign from the list.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Campaign to Load")
        self.resize(800, 500) # Spacious default size
        
        self.selected_campaign_id = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Campaign List
        self.list_widget = CampaignListWidget()
        self.list_widget.campaign_double_clicked.connect(self.on_double_click)
        layout.addWidget(self.list_widget)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        select_btn = QPushButton("Load Selected")
        select_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        select_btn.clicked.connect(self.accept_selection)
        btn_layout.addWidget(select_btn)
        
        layout.addLayout(btn_layout)
        
    def on_double_click(self, camp_id):
        self.selected_campaign_id = camp_id
        self.accept()
        
    def accept_selection(self):
        self.selected_campaign_id = self.list_widget.get_selected_campaign_id()
        if self.selected_campaign_id:
            self.accept()
            
    def get_selected_id(self):
        return self.selected_campaign_id
