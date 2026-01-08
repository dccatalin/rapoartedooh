"""
Document Edit Dialog - Add/Edit individual documents with file upload
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                             QComboBox, QDateEdit, QPushButton, QTextEdit,
                             QDialogButtonBox, QFileDialog, QMessageBox, QHBoxLayout,
                             QLabel, QGroupBox)
from PyQt6.QtCore import QDate
import datetime
import os

from src.data.document_manager import DocumentManager

class DocumentEditDialog(QDialog):
    """Dialog for adding or editing a single document"""
    
    def __init__(self, parent=None, entity_type='vehicle', entity_id=None, document_data=None):
        super().__init__(parent)
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.document_data = document_data
        self.doc_manager = DocumentManager()
        self.selected_file_path = None
        
        title = "Edit Document" if document_data else "Add Document"
        self.setWindowTitle(title)
        self.resize(500, 600)
        self.init_ui()
        
        if document_data:
            self.load_data()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # Document Type
        self.type_combo = QComboBox()
        if self.entity_type == 'vehicle':
            self.type_combo.addItems(self.doc_manager.VEHICLE_TYPES)
        else:
            self.type_combo.addItems(self.doc_manager.DRIVER_TYPES)
        
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        form.addRow("Document Type:", self.type_combo)
        
        # Custom Type Name (only visible for Custom type)
        self.custom_name_input = QLineEdit()
        self.custom_name_input.setPlaceholderText("Enter custom document type name")
        self.custom_name_row = form.rowCount()
        form.addRow("Custom Type Name:", self.custom_name_input)
        self.custom_name_input.setVisible(False)
        
        # Issue Date
        self.issue_date = QDateEdit()
        self.issue_date.setCalendarPopup(True)
        self.issue_date.setDate(QDate.currentDate())
        self.issue_date.setSpecialValueText("Not Set")
        self.issue_date.setDisplayFormat("yyyy-MM-dd")
        
        issue_layout = QHBoxLayout()
        issue_layout.addWidget(self.issue_date)
        clear_issue_btn = QPushButton("Clear")
        clear_issue_btn.clicked.connect(lambda: self.issue_date.setDate(QDate(2000, 1, 1)))
        issue_layout.addWidget(clear_issue_btn)
        
        form.addRow("Issue Date:", issue_layout)
        
        # Expiry Date
        self.expiry_date = QDateEdit()
        self.expiry_date.setCalendarPopup(True)
        self.expiry_date.setDate(QDate.currentDate().addYears(1))
        self.expiry_date.setSpecialValueText("No Expiry")
        self.expiry_date.setDisplayFormat("yyyy-MM-dd")
        
        expiry_layout = QHBoxLayout()
        expiry_layout.addWidget(self.expiry_date)
        clear_expiry_btn = QPushButton("Clear")
        clear_expiry_btn.clicked.connect(lambda: self.expiry_date.setDate(QDate(2000, 1, 1)))
        expiry_layout.addWidget(clear_expiry_btn)
        
        form.addRow("Expiry Date:", expiry_layout)
        
        layout.addLayout(form)
        
        # File Upload Section
        file_group = QGroupBox("Document File")
        file_layout = QVBoxLayout()
        
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("padding: 5px; background-color: #f0f0f0; border-radius: 3px;")
        file_layout.addWidget(self.file_label)
        
        file_btn_layout = QHBoxLayout()
        
        choose_btn = QPushButton("Choose File")
        choose_btn.clicked.connect(self.choose_file)
        file_btn_layout.addWidget(choose_btn)
        
        self.view_btn = QPushButton("View File")
        self.view_btn.clicked.connect(self.view_file)
        self.view_btn.setEnabled(False)
        file_btn_layout.addWidget(self.view_btn)
        
        self.remove_btn = QPushButton("Remove File")
        self.remove_btn.clicked.connect(self.remove_file)
        self.remove_btn.setEnabled(False)
        file_btn_layout.addWidget(self.remove_btn)
        
        file_layout.addLayout(file_btn_layout)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Notes
        notes_label = QLabel("Notes:")
        layout.addWidget(notes_label)
        
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Additional notes or comments...")
        self.notes_input.setMaximumHeight(100)
        layout.addWidget(self.notes_input)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def on_type_changed(self, doc_type):
        """Show/hide custom type name field"""
        is_custom = doc_type == 'Custom'
        self.custom_name_input.setVisible(is_custom)
        if is_custom:
            self.custom_name_input.setFocus()
    
    def choose_file(self):
        """Open file dialog to select document file"""
        file_filter = "Documents (*.pdf *.jpg *.jpeg *.png);;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Document File",
            "",
            file_filter
        )
        
        if file_path:
            # Validate file size
            file_size = os.path.getsize(file_path)
            if file_size > self.doc_manager.MAX_FILE_SIZE:
                QMessageBox.warning(
                    self,
                    "File Too Large",
                    f"File size ({file_size / 1024 / 1024:.1f} MB) exceeds the maximum allowed size (10 MB)."
                )
                return
            
            # Validate file extension
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in self.doc_manager.ALLOWED_EXTENSIONS:
                QMessageBox.warning(
                    self,
                    "Invalid File Type",
                    f"File type '{ext}' is not allowed. Please select a PDF or image file."
                )
                return
            
            self.selected_file_path = file_path
            self.file_label.setText(os.path.basename(file_path))
            self.view_btn.setEnabled(True)
            self.remove_btn.setEnabled(True)
    
    def view_file(self):
        """Open the selected file for viewing"""
        if not self.selected_file_path and self.document_data:
            # View existing file
            file_path = self.doc_manager.get_document_file_path(self.document_data['id'])
            if file_path and os.path.exists(file_path):
                self._open_file(file_path)
            else:
                QMessageBox.warning(self, "File Not Found", "The document file could not be found.")
        elif self.selected_file_path:
            # View newly selected file
            self._open_file(self.selected_file_path)
    
    def _open_file(self, file_path):
        """Open file with default application"""
        import subprocess
        import platform
        
        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', file_path])
            elif platform.system() == 'Windows':
                os.startfile(file_path)
            else:  # Linux
                subprocess.call(['xdg-open', file_path])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file: {e}")
    
    def remove_file(self):
        """Remove the selected file"""
        self.selected_file_path = None
        self.file_label.setText("No file selected")
        self.view_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
    
    def load_data(self):
        """Load existing document data into form"""
        if not self.document_data:
            return
        
        # Set document type
        doc_type = self.document_data['document_type']
        index = self.type_combo.findText(doc_type)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)
        
        # Set custom type name if applicable
        if doc_type == 'Custom' and self.document_data.get('custom_type_name'):
            self.custom_name_input.setText(self.document_data['custom_type_name'])
        
        # Set dates
        if self.document_data.get('issue_date'):
            issue_date = self.document_data['issue_date']
            if isinstance(issue_date, str):
                issue_date = datetime.date.fromisoformat(issue_date)
            self.issue_date.setDate(QDate(issue_date.year, issue_date.month, issue_date.day))
        
        if self.document_data.get('expiry_date'):
            expiry_date = self.document_data['expiry_date']
            if isinstance(expiry_date, str):
                expiry_date = datetime.date.fromisoformat(expiry_date)
            self.expiry_date.setDate(QDate(expiry_date.year, expiry_date.month, expiry_date.day))
        
        # Set file info
        if self.document_data.get('file_name'):
            self.file_label.setText(self.document_data['file_name'])
            self.view_btn.setEnabled(True)
            # Don't enable remove button for existing files (would need special handling)
        
        # Set notes
        if self.document_data.get('notes'):
            self.notes_input.setText(self.document_data['notes'])
    
    def save(self):
        """Save the document"""
        # Validate
        doc_type = self.type_combo.currentText()
        if doc_type == 'Custom' and not self.custom_name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a custom type name.")
            return
        
        # Prepare data
        issue_date = self.issue_date.date().toPyDate() if self.issue_date.date().year() > 2000 else None
        expiry_date = self.expiry_date.date().toPyDate() if self.expiry_date.date().year() > 2000 else None
        custom_name = self.custom_name_input.text().strip() if doc_type == 'Custom' else None
        notes = self.notes_input.toPlainText().strip()
        
        try:
            if self.document_data:
                # Update existing document
                updates = {
                    'document_type': doc_type,
                    'custom_type_name': custom_name,
                    'issue_date': issue_date,
                    'expiry_date': expiry_date,
                    'notes': notes
                }
                
                success = self.doc_manager.update_document(
                    self.document_data['id'],
                    updates,
                    self.selected_file_path
                )
                
                if success:
                    QMessageBox.information(self, "Success", "Document updated successfully.")
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", "Failed to update document.")
            else:
                # Add new document
                doc_id = self.doc_manager.add_document(
                    self.entity_type,
                    self.entity_id,
                    doc_type,
                    expiry_date=expiry_date,
                    issue_date=issue_date,
                    custom_type_name=custom_name,
                    notes=notes,
                    file_path=self.selected_file_path
                )
                
                if doc_id:
                    QMessageBox.information(self, "Success", "Document added successfully.")
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", "Failed to add document.")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")
