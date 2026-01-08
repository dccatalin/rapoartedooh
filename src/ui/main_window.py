from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, 
                               QPushButton, QMessageBox, QFrame, QApplication, QMenuBar, QTabWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import sys
import os

# Add src to path to ensure imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.campaign_report_dialog import CampaignReportDialog
from src.reporting.campaign_report_generator import CampaignReportGenerator
from src.data.city_data_manager import CityDataManager
from src.ui.city_manager_dialog import CityManagerDialog
from src.ui.company_settings_dialog import CompanySettingsDialog
from src.ui.fleet_management_dialog import FleetManagementDialog
from src.ui.campaign_calendar_view import CampaignCalendarView
from src.ui.fleet_reports_dialog import FleetReportsDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mobile DOOH Management")
        self.resize(1000, 700)
        self.setMinimumSize(800, 600)
        
        # Initialize managers
        self.city_manager = CityDataManager()
        self.report_generator = CampaignReportGenerator(data_manager=None)
        
        self.init_ui()
        self.create_menu_bar()
        self.center_on_screen()
        
    def init_ui(self):
        # Create central tab widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # --- Tab 1: Dashboard (Existing UI) ---
        self.dashboard_tab = QWidget()
        self.init_dashboard_tab()
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        
        # --- Tab 2: Campaign Management ---
        from src.ui.campaign_manager_tab import CampaignManagerTab
        self.campaign_tab = CampaignManagerTab()
        self.tabs.addTab(self.campaign_tab, "Campaigns")
        
    def init_dashboard_tab(self):
        layout = QVBoxLayout(self.dashboard_tab)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Title
        title = QLabel("Mobile DOOH Management")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Generate comprehensive campaign reports with audience estimation.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #666; font-size: 14px;")
        layout.addWidget(subtitle)
        
        layout.addStretch()
        
        # Main Action Button
        self.generate_btn = QPushButton("Create New Campaign")
        self.generate_btn.setMinimumHeight(60)
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 18px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.generate_btn.clicked.connect(self.start_campaign_flow)
        layout.addWidget(self.generate_btn)
        
        # Manage Cities Button
        self.manage_cities_btn = QPushButton("Manage Cities & Events")
        self.manage_cities_btn.setMinimumHeight(50)
        self.manage_cities_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        self.manage_cities_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.manage_cities_btn.clicked.connect(self.open_city_manager)
        layout.addWidget(self.manage_cities_btn)
        
        # Fleet Management Button
        fleet_management_btn = QPushButton("Fleet Management")
        fleet_management_btn.setMinimumHeight(50)
        fleet_management_btn.setStyleSheet("""
            QPushButton {
                background-color: #009688;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #00796B;
            }
        """)
        fleet_management_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fleet_management_btn.clicked.connect(self.open_fleet_management)
        layout.addWidget(fleet_management_btn)

        # Fleet Calendar Button
        fleet_calendar_btn = QPushButton("Fleet Calendar")
        fleet_calendar_btn.setMinimumHeight(50)
        fleet_calendar_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        fleet_calendar_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fleet_calendar_btn.clicked.connect(self.open_calendar)
        layout.addWidget(fleet_calendar_btn)
        
        # Fleet Reports Button
        fleet_reports_btn = QPushButton("Fleet Reports")
        fleet_reports_btn.setMinimumHeight(50)
        fleet_reports_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        fleet_reports_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fleet_reports_btn.clicked.connect(self.open_fleet_reports)
        layout.addWidget(fleet_reports_btn)
        
        # Company Details Button
        company_btn = QPushButton("Company Details")
        company_btn.setMinimumHeight(40)
        company_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        company_btn.clicked.connect(self.open_company_settings)
        layout.addWidget(company_btn)
        
        layout.addStretch()
        
        # Footer
        footer = QLabel("v9.4 - Multi-Vehicle System")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #999; font-size: 10px;")
        layout.addWidget(footer)

    def show_help(self):
        from src.ui.help_dialog import HelpDialog
        dialog = HelpDialog(self)
        dialog.exec()
        
    def show_about(self):
        QMessageBox.about(
            self,
            "About Raportare DOOH",
            "Raportare DOOH v9.0\n\n"
            "Advanced Campaign Management & Analytics\n"
            "Features: ROI, Route Optimization, Financial Reports"
        )
    
    def create_menu_bar(self):
        """Create menu bar with Tools menu"""
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("File")
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        # City Manager
        city_action = tools_menu.addAction("Manage Cities & Events")
        city_action.triggered.connect(self.open_city_manager)
        
        # Calendar View
        calendar_action = tools_menu.addAction("Fleet Calendar")
        calendar_action.triggered.connect(self.open_calendar)
        
        # Fleet Reports
        reports_action = tools_menu.addAction("Fleet Reports")
        reports_action.triggered.connect(self.open_fleet_reports)

        # Settings Menu
        settings_menu = menubar.addMenu("Settings")
        
        company_action = settings_menu.addAction("Company Details")
        company_action.triggered.connect(self.open_company_settings)
        
        fleet_action = settings_menu.addAction("Fleet Management")
        fleet_action.triggered.connect(self.open_fleet_management)

        # Help Menu
        help_menu = menubar.addMenu("Help")
        
        help_action = help_menu.addAction("Documentation")
        help_action.triggered.connect(self.show_help)
        
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)
    
    def open_company_settings(self):
        """Open company settings dialog"""
        dialog = CompanySettingsDialog(self)
        dialog.exec()
        
    def open_fleet_management(self):
        """Open fleet management dialog"""
        dialog = FleetManagementDialog(self)
        dialog.exec()
        
    def open_calendar(self):
        """Open campaign calendar view"""
        dialog = CampaignCalendarView(self)
        dialog.exec()
        
    def open_fleet_reports(self):
        """Open fleet reports dialog"""
        dialog = FleetReportsDialog(self)
        dialog.exec()
    
    def open_city_manager(self):
        """Open the city manager dialog"""
        dialog = CityManagerDialog(self)
        dialog.exec()
    
    def center_on_screen(self):
        """Center the window on the screen"""
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.frameGeometry()
        center_point = screen.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())
        
    def start_campaign_flow(self):
        """Open the campaign configuration dialog"""
        dialog = CampaignReportDialog(self)
        if dialog.exec():
            # Check if user requested report generation
            if getattr(dialog, 'should_generate_report', False):
                campaign_data = dialog.get_data()
                self.generate_report(campaign_data)
            
    def generate_report(self, campaign_data):
        """Generate the report with the provided data"""
        try:
            # Show loading state (simple blocking for now as it's fast enough)
            self.generate_btn.setText("Generating Report...")
            self.generate_btn.setEnabled(False)
            QApplication.processEvents()
            
            # Get default output path from settings
            from src.data.company_settings import CompanySettings
            settings = CompanySettings().get_settings()
            output_dir = settings.get('reports_output_path')
            
            output_path = self.report_generator.generate_campaign_report(campaign_data, output_dir=output_dir)
            
            self.generate_btn.setText("Create New Campaign")
            self.generate_btn.setEnabled(True)
            
            # Success feedback via status bar or log instead of popup
            # self.statusBar().showMessage(f"Report saved to: {output_path}", 5000)
            print(f"Report generated: {output_path}")
            
        except Exception as e:
            self.generate_btn.setText("Create New Campaign")
            self.generate_btn.setEnabled(True)
            QMessageBox.critical(self, "Error", f"Failed to generate report: {str(e)}")

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
