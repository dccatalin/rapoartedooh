from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, QLabel)
from src.data.campaign_storage import CampaignStorage
from src.ui.campaign_report_dialog import CampaignReportDialog
from src.ui.campaign_list_widget import CampaignListWidget

class CampaignManagerTab(QWidget):
    """
    Tab for managing campaigns: listing, editing, deleting.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.storage = CampaignStorage()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Reusable List Widget
        self.list_widget = CampaignListWidget()
        self.list_widget.campaign_double_clicked.connect(self.edit_selected_campaign)
        layout.addWidget(self.list_widget)
        
        # --- Bottom Action Bar ---
        action_bar = QHBoxLayout()
        
        edit_btn = QPushButton("Edit Selected")
        edit_btn.clicked.connect(self.edit_selected_campaign)
        action_bar.addWidget(edit_btn)
        
        clone_btn = QPushButton("Duplicate Selected")
        clone_btn.setToolTip("Create a copy of the selected campaign")
        clone_btn.clicked.connect(self.clone_selected_campaign)
        action_bar.addWidget(clone_btn)
        
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet("background-color: #f44336; color: white;")
        delete_btn.clicked.connect(self.delete_selected_campaign)
        action_bar.addWidget(delete_btn)
        
        action_bar.addStretch()
        
        layout.addLayout(action_bar)
        
    def load_campaigns(self):
        """Proxy to reload list"""
        self.list_widget.load_campaigns()
        
    def edit_selected_campaign(self, camp_id=None):
        """Open dialog to edit selected campaign"""
        if not camp_id:
            camp_id = self.list_widget.get_selected_campaign_id()
            
        if not camp_id:
            return
            
        # Get full data
        campaign_data = self.storage.get_campaign(camp_id)
        if not campaign_data:
            QMessageBox.warning(self, "Error", "Campaign not found!")
            self.load_campaigns()
            return
            
        # Open dialog
        dialog = CampaignReportDialog(self)
        # Assuming we eventually want to use set_data here or similar
        # For now, let's use the method we know works/will work
        dialog.load_campaign(campaign_data)
        
        if dialog.exec():
            # If saved, refresh list
            self.load_campaigns()
            
    def delete_selected_campaign(self):
        """Delete selected campaign"""
        camp_id = self.list_widget.get_selected_campaign_id()
        if not camp_id:
            return
            
        # Confirm
        reply = QMessageBox.question(
            self,
            "Delete Campaign",
            "Are you sure you want to delete this campaign?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.storage.delete_campaign(camp_id):
                self.load_campaigns()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete campaign.")

    def clone_selected_campaign(self):
        """Clone selected campaign"""
        camp_id = self.list_widget.get_selected_campaign_id()
        if not camp_id:
            return
            
        # Confirm
        reply = QMessageBox.question(
            self,
            "Duplicate Campaign",
            "Are you sure you want to duplicate this campaign?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            new_id = self.storage.clone_campaign(camp_id)
            if new_id:
                self.load_campaigns()
                QMessageBox.information(self, "Success", "Campaign duplicated successfully.")
            else:
                QMessageBox.warning(self, "Error", "Failed to duplicate campaign.")
