"""
Document Management Dialog - Main UI for viewing and managing documents
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
                             QMessageBox, QAbstractItemView, QLabel, QMenu)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import datetime
import os
import subprocess
import platform

from src.data.document_manager import DocumentManager

class DocumentManagementDialog(QDialog):
    """Dialog for managing all documents for a vehicle or driver"""
    
    def __init__(self, parent=None, entity_type='vehicle', entity_id=None, entity_name=''):
        super().__init__(parent)
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.entity_name = entity_name
        self.doc_manager = DocumentManager()
        
        self.setWindowTitle(f"Document Management - {entity_name}")
        self.resize(900, 600)
        self.init_ui()
        self.load_documents()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel(f"Documents for {self.entity_type.capitalize()}: {self.entity_name}")
        header.setStyleSheet("font-weight: bold; font-size: 14px; padding: 10px;")
        layout.addWidget(header)
        
        # Filter bar
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Documents", "Valid", "Expiring Soon", "Expired", "No Expiry"])
        self.filter_combo.currentTextChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.filter_combo)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Type", "Issue Date", "Expiry Date", "Status", "File", "Notes", "ID"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnHidden(6, True)  # Hide ID column
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.edit_document)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Document")
        add_btn.clicked.connect(self.add_document)
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self.edit_document)
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self.delete_document)
        btn_layout.addWidget(delete_btn)
        
        view_btn = QPushButton("View File")
        view_btn.clicked.connect(self.view_file)
        btn_layout.addWidget(view_btn)
        
        btn_layout.addStretch()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_documents)
        btn_layout.addWidget(refresh_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def load_documents(self):
        """Load all documents from database"""
        self.documents = self.doc_manager.get_documents(self.entity_type, self.entity_id)
        self.apply_filter()
    
    def apply_filter(self):
        """Apply current filter to document list"""
        filter_text = self.filter_combo.currentText()
        
        self.table.setRowCount(0)
        
        for doc in self.documents:
            # Apply filter
            if filter_text == "Valid" and doc['status'] != 'valid':
                continue
            elif filter_text == "Expiring Soon" and doc['status'] != 'expiring':
                continue
            elif filter_text == "Expired" and doc['status'] != 'expired':
                continue
            elif filter_text == "No Expiry" and doc['status'] != 'no_expiry':
                continue
            
            self._add_table_row(doc)
        
        # Update header with count
        count = self.table.rowCount()
        total = len(self.documents)
        self.setWindowTitle(f"Document Management - {self.entity_name} ({count}/{total})")
    
    def _add_table_row(self, doc):
        """Add a document to the table"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Type
        doc_type = doc['document_type']
        if doc_type == 'Custom' and doc['custom_type_name']:
            doc_type = doc['custom_type_name']
        self.table.setItem(row, 0, QTableWidgetItem(doc_type))
        
        # Issue Date
        issue_date = doc['issue_date'].strftime('%Y-%m-%d') if doc['issue_date'] else '-'
        self.table.setItem(row, 1, QTableWidgetItem(issue_date))
        
        # Expiry Date
        expiry_date = doc['expiry_date'].strftime('%Y-%m-%d') if doc['expiry_date'] else '-'
        self.table.setItem(row, 2, QTableWidgetItem(expiry_date))
        
        # Status
        status_item = QTableWidgetItem(self._get_status_text(doc['status']))
        status_item.setForeground(self._get_status_color(doc['status']))
        if doc['status'] == 'expired':
            font = status_item.font()
            font.setBold(True)
            status_item.setFont(font)
        self.table.setItem(row, 3, status_item)
        
        # File
        file_text = doc['file_name'] if doc['file_name'] else 'No file'
        self.table.setItem(row, 4, QTableWidgetItem(file_text))
        
        # Notes
        notes = doc['notes'] if doc['notes'] else ''
        self.table.setItem(row, 5, QTableWidgetItem(notes))
        
        # ID (hidden)
        self.table.setItem(row, 6, QTableWidgetItem(doc['id']))
    
    def _get_status_text(self, status):
        """Get display text for status"""
        status_map = {
            'valid': 'Valid',
            'expiring': 'Expiring Soon',
            'expired': 'EXPIRED',
            'no_expiry': 'No Expiry'
        }
        return status_map.get(status, status)
    
    def _get_status_color(self, status):
        """Get color for status"""
        color_map = {
            'valid': QColor(0, 128, 0),      # Green
            'expiring': QColor(255, 140, 0),  # Orange
            'expired': QColor(255, 0, 0),     # Red
            'no_expiry': QColor(128, 128, 128) # Gray
        }
        return color_map.get(status, QColor(0, 0, 0))
    
    def add_document(self):
        """Open dialog to add new document"""
        from src.ui.document_edit_dialog import DocumentEditDialog
        
        dialog = DocumentEditDialog(self, self.entity_type, self.entity_id)
        if dialog.exec():
            self.load_documents()
    
    def edit_document(self):
        """Edit selected document"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a document to edit.")
            return
        
        doc_id = self.table.item(row, 6).text()
        doc_data = self.doc_manager.get_document(doc_id)
        
        from src.ui.document_edit_dialog import DocumentEditDialog
        dialog = DocumentEditDialog(self, self.entity_type, self.entity_id, doc_data)
        if dialog.exec():
            self.load_documents()
    
    def delete_document(self):
        """Delete selected document"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a document to delete.")
            return
        
        doc_type = self.table.item(row, 0).text()
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the document '{doc_type}'?\nThis will also delete any uploaded file.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            doc_id = self.table.item(row, 6).text()
            if self.doc_manager.delete_document(doc_id):
                QMessageBox.information(self, "Success", "Document deleted successfully.")
                self.load_documents()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete document.")
    
    def view_file(self):
        """Open the document file"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a document.")
            return
        
        doc_id = self.table.item(row, 6).text()
        file_path = self.doc_manager.get_document_file_path(doc_id)
        
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "No File", "This document has no uploaded file.")
            return
        
        # Open file with default application
        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', file_path])
            elif platform.system() == 'Windows':
                os.startfile(file_path)
            else:  # Linux
                subprocess.call(['xdg-open', file_path])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file: {e}")
    
    def show_context_menu(self, position):
        """Show context menu on right-click"""
        menu = QMenu(self)
        
        edit_action = menu.addAction("Edit")
        edit_action.triggered.connect(self.edit_document)
        
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(self.delete_document)
        
        menu.addSeparator()
        
        view_action = menu.addAction("View File")
        view_action.triggered.connect(self.view_file)
        
        open_folder_action = menu.addAction("Open Folder")
        open_folder_action.triggered.connect(self.open_folder)
        
        menu.exec(self.table.viewport().mapToGlobal(position))
    
    def open_folder(self):
        """Open the folder containing document files"""
        folder_path = os.path.join(self.doc_manager.DOCUMENTS_DIR, 
                                   f"{self.entity_type}s", self.entity_id)
        
        if not os.path.exists(folder_path):
            QMessageBox.information(self, "No Folder", "No documents folder exists yet.")
            return
        
        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', folder_path])
            elif platform.system() == 'Windows':
                os.startfile(folder_path)
            else:  # Linux
                subprocess.call(['xdg-open', folder_path])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open folder: {e}")
