import sys
import os
from PyQt6.QtWidgets import QApplication

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'Numarare'))

from src.ui.campaign_report_dialog import CampaignReportDialog
from src.ui.reports_window import ReportsWindow

class MockDataManager:
    def get_setting(self, key, default=None):
        return default

class MockAppManager:
    def __init__(self):
        self.data_manager = MockDataManager()

def test_ui():
    app = QApplication(sys.argv)
    
    print("Testing CampaignReportDialog instantiation...")
    try:
        dialog = CampaignReportDialog()
        print("CampaignReportDialog instantiated successfully.")
    except Exception as e:
        print(f"Failed to instantiate CampaignReportDialog: {e}")
        return

    print("Testing ReportsWindow instantiation...")
    try:
        app_manager = MockAppManager()
        window = ReportsWindow(app_manager)
        print("ReportsWindow instantiated successfully.")
    except Exception as e:
        print(f"Failed to instantiate ReportsWindow: {e}")
        return
        
    print("UI Integration Test Passed.")

if __name__ == "__main__":
    test_ui()
