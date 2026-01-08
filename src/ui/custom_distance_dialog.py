from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QDoubleSpinBox,
                              QDialogButtonBox, QLabel, QScrollArea, QWidget)
from PyQt6.QtCore import QDate
import datetime

class CustomDistanceDialog(QDialog):
    def __init__(self, parent=None, start_date=None, end_date=None):
        super().__init__(parent)
        self.setWindowTitle("Distanta pe Fiecare Zi")
        self.resize(400, 500)
        
        # Convert QDate to datetime.date if needed
        if isinstance(start_date, QDate):
            start_date = datetime.date(start_date.year(), start_date.month(), start_date.day())
        if isinstance(end_date, QDate):
            end_date = datetime.date(end_date.year(), end_date.month(), end_date.day())
            
        self.start_date = start_date
        self.end_date = end_date
        self.distance_inputs = {}
        
        self.init_ui()
        self.center_on_screen()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Info label
        info = QLabel("Introduceti distanta parcursa pentru fiecare zi a campaniei (km).")
        layout.addWidget(info)
        
        # Scroll area for days
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QFormLayout(scroll_widget)
        
        # Create input for each day
        current_date = self.start_date
        while current_date <= self.end_date:
            day_label = current_date.strftime("%A, %d %B %Y")
            day_input = QDoubleSpinBox()
            day_input.setRange(0, 1000)
            day_input.setValue(0)
            day_input.setSuffix(" km")
            day_input.setDecimals(1)
            
            scroll_layout.addRow(day_label, day_input)
            self.distance_inputs[current_date] = day_input
            
            current_date += datetime.timedelta(days=1)
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_distances(self):
        """Return dictionary of date -> distance (km)"""
        distances = {}
        for date, input_widget in self.distance_inputs.items():
            distances[date] = input_widget.value()
        return distances
    
    def center_on_screen(self):
        """Center the dialog on the screen"""
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.frameGeometry()
        center_point = screen.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())
