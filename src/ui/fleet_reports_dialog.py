"""
Fleet Reports Dialog
UI for generating fleet utilization and driver performance reports.
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QDateEdit, QMessageBox, QGroupBox, QFormLayout)
from PyQt6.QtCore import Qt, QDate
import datetime
from src.reporting.fleet_utilization_report import FleetUtilizationReportGenerator

class FleetReportsDialog(QDialog):
    """Dialog for generating fleet reports"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fleet Reports")
        self.resize(500, 400)
        
        self.generator = FleetUtilizationReportGenerator()
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Fleet Utilization & Performance Reports")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        layout.addSpacing(20)
        
        # Date Range Selection
        date_group = QGroupBox("Report Period")
        date_layout = QFormLayout()
        
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        date_layout.addRow("Start Date:", self.start_date)
        
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        date_layout.addRow("End Date:", self.end_date)
        
        date_group.setLayout(date_layout)
        layout.addWidget(date_group)
        
        layout.addSpacing(20)
        
        # Report Buttons
        reports_group = QGroupBox("Available Reports")
        reports_layout = QVBoxLayout()
        
        # Vehicle Utilization Report
        vehicle_btn = QPushButton("Generate Vehicle Utilization Report")
        vehicle_btn.setMinimumHeight(50)
        vehicle_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        vehicle_btn.clicked.connect(self.generate_vehicle_report)
        reports_layout.addWidget(vehicle_btn)
        
        # Driver Performance Report
        driver_btn = QPushButton("Generate Driver Performance Report")
        driver_btn.setMinimumHeight(50)
        driver_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        driver_btn.clicked.connect(self.generate_driver_report)
        reports_layout.addWidget(driver_btn)
        
        reports_group.setLayout(reports_layout)
        layout.addWidget(reports_group)
        
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
    def generate_vehicle_report(self):
        """Generate vehicle utilization report"""
        start = self.start_date.date().toPyDate()
        end = self.end_date.date().toPyDate()
        
        if start > end:
            QMessageBox.warning(self, "Invalid Dates", "Start date must be before end date")
            return
            
        try:
            self.generator.generate_vehicle_utilization_report(start, end)
            QMessageBox.information(self, "Success", "Vehicle utilization report generated successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate report: {str(e)}")
            
    def generate_driver_report(self):
        """Generate driver performance report"""
        start = self.start_date.date().toPyDate()
        end = self.end_date.date().toPyDate()
        
        if start > end:
            QMessageBox.warning(self, "Invalid Dates", "Start date must be before end date")
            return
            
        try:
            self.generator.generate_driver_performance_report(start, end)
            QMessageBox.information(self, "Success", "Driver performance report generated successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate report: {str(e)}")
