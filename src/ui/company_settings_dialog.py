from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                               QPushButton, QLabel, QFileDialog, QHBoxLayout, 
                               QDialogButtonBox, QMessageBox, QGroupBox)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import os
from src.data.company_settings import CompanySettings

class CompanySettingsDialog(QDialog):
    """Dialog for managing company settings (Logo, Name, Address)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Company Settings")
        self.resize(600, 700)
        
        self.settings_manager = CompanySettings()
        self.settings = self.settings_manager.get_settings()
        
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Scroll Area
        from PyQt6.QtWidgets import QScrollArea, QWidget
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        
        # Form
        form_group = QGroupBox("Company Details")
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., My Media Agency SRL")
        self.name_input.setText(self.settings.get('name', ''))
        form_layout.addRow("Company Name:", self.name_input)
        
        self.reg_input = QLineEdit()
        self.reg_input.setPlaceholderText("e.g., J40/123/2024, RO123456")
        self.reg_input.setText(self.settings.get('registration_number', ''))
        form_layout.addRow("Reg. Number / CUI:", self.reg_input)
        
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("e.g., Str. Victoriei 10, Bucuresti")
        self.address_input.setText(self.settings.get('address', ''))
        form_layout.addRow("Address:", self.address_input)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # API Keys Group
        keys_group = QGroupBox("Map Service Keys")
        keys_layout = QFormLayout()
        
        # Google Maps
        self.google_key_input = QLineEdit()
        self.google_key_input.setPlaceholderText("Google Maps API Key")
        self.google_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.google_key_input.setText(self.settings.get('google_maps_api_key', ''))
        
        google_label = QLabel('<a href="https://developers.google.com/maps/documentation/maps-static/get-api-key">Get Key</a>')
        google_label.setOpenExternalLinks(True)
        
        keys_layout.addRow("Google Maps:", self.google_key_input)
        keys_layout.addRow("", google_label)
        
        # Mapbox
        self.mapbox_key_input = QLineEdit()
        self.mapbox_key_input.setPlaceholderText("Mapbox Access Token")
        self.mapbox_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.mapbox_key_input.setText(self.settings.get('mapbox_api_key', ''))
        
        mapbox_label = QLabel('<a href="https://account.mapbox.com/access-tokens/">Get Token</a>')
        mapbox_label.setOpenExternalLinks(True)
        
        keys_layout.addRow("Mapbox:", self.mapbox_key_input)
        keys_layout.addRow("", mapbox_label)
        
        keys_group.setLayout(keys_layout)
        layout.addWidget(keys_group)
        
        # Logo
        logo_group = QGroupBox("Company Logo")
        logo_layout = QVBoxLayout()
        
        self.logo_path = self.settings.get('logo_path', '')
        self.logo_label = QLabel("No Logo Selected")
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setMinimumHeight(100)
        self.logo_label.setStyleSheet("border: 1px dashed #ccc; background: #f9f9f9;")
        
        if self.logo_path and os.path.exists(self.logo_path):
            self.update_logo_preview(self.logo_path)
            
        logo_layout.addWidget(self.logo_label)
        
        btn_layout = QHBoxLayout()
        select_btn = QPushButton("Select Logo...")
        select_btn.clicked.connect(self.select_logo)
        btn_layout.addWidget(select_btn)
        
        clear_btn = QPushButton("Clear Logo")
        clear_btn.clicked.connect(self.clear_logo)
        btn_layout.addWidget(clear_btn)
        
        logo_layout.addLayout(btn_layout)
        logo_group.setLayout(logo_layout)
        layout.addWidget(logo_group)
        
        # Reports Settings Group
        reports_group = QGroupBox("Reports Configuration")
        reports_layout = QVBoxLayout()
        
        path_layout = QHBoxLayout()
        self.output_path_input = QLineEdit()
        self.output_path_input.setPlaceholderText("Default Reports Output Folder")
        self.output_path_input.setText(self.settings.get('reports_output_path', ''))
        path_layout.addWidget(self.output_path_input)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_output_path)
        path_layout.addWidget(browse_btn)
        
        reports_layout.addWidget(QLabel("Default Output Folder:"))
        reports_layout.addLayout(path_layout)
        reports_group.setLayout(reports_layout)
        layout.addWidget(reports_group)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
    def browse_output_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Reports Output Folder")
        if folder:
            self.output_path_input.setText(folder)
            
    def select_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Logo", "", "Images (*.png *.jpg *.jpeg *.svg);;All Files (*)"
        )
        
        if file_path:
            self.logo_path = file_path
            self.update_logo_preview(file_path)
            
    def clear_logo(self):
        self.logo_path = ""
        self.logo_label.setText("No Logo Selected")
        self.logo_label.setPixmap(QPixmap())
        
    def update_logo_preview(self, path):
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(200, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(scaled)
        else:
            self.logo_label.setText("Invalid Image")
            
    def save_settings(self):
        name = self.name_input.text().strip()
        address = self.address_input.text().strip()
        reg_number = self.reg_input.text().strip()
        
        google_key = self.google_key_input.text().strip()
        mapbox_key = self.mapbox_key_input.text().strip()
        output_path = self.output_path_input.text().strip()
        
        if self.settings_manager.save_settings(name, address, self.logo_path, reg_number, google_key, mapbox_key, output_path):
            QMessageBox.information(self, "Success", "Company settings saved successfully.")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to save settings.")
