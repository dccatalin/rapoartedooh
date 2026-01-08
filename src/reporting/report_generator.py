from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import datetime
import io
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import os
import subprocess

class ReportGenerator:
    def __init__(self, data_manager=None):
        # data_manager is optional in standalone mode
        self.data_manager = data_manager
        self.styles = getSampleStyleSheet()
        # Reports dir relative to the standalone app root
        self.reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'reports')
        self._ensure_reports_dir()
        
    def _ensure_reports_dir(self):
        """Ensure reports directory exists"""
        if not os.path.exists(self.reports_dir):
            os.makedirs(self.reports_dir)
    
    def _get_report_path(self, filename):
        """Get full path for report in reports directory"""
        return os.path.join(self.reports_dir, filename)
    
    def _open_report(self, filepath):
        """Open the generated report with default PDF viewer"""
        try:
            if os.path.exists(filepath):
                import sys
                if sys.platform == 'darwin':  # macOS
                    subprocess.run(['open', filepath], check=True)
                elif sys.platform == 'win32': # Windows
                    os.startfile(filepath)
                else: # Linux
                    subprocess.run(['xdg-open', filepath])
        except Exception as e:
            print(f"Could not open report: {e}")
        
    def create_time_series_chart(self, hourly_data, title="Hourly Activity"):
        """Create a time series chart for hourly data"""
        if not hourly_data:
            return None
            
        fig, ax = plt.subplots(figsize=(10, 4))
        
        hours = sorted(hourly_data.keys())
        people_counts = [hourly_data[h].get('person', 0) for h in hours]
        car_counts = [
            hourly_data[h].get('car', 0) + 
            hourly_data[h].get('truck', 0) + 
            hourly_data[h].get('bus', 0) + 
            hourly_data[h].get('train', 0) 
            for h in hours
        ]
        
        hour_labels = [h.strftime('%H:%M') for h in hours]
        
        ax.plot(hour_labels, people_counts, marker='o', label='People', linewidth=2)
        ax.plot(hour_labels, car_counts, marker='s', label='Vehicles', linewidth=2)
        
        ax.set_xlabel('Time')
        ax.set_ylabel('Count')
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Rotate labels if too many
        if len(hour_labels) > 12:
            plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Save to bytes
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    def create_pie_chart(self, data, title="Distribution"):
        """Create a pie chart from dictionary data or list of tuples"""
        if not data:
            return None
            
        if isinstance(data, list):
            data_dict = dict(data)
        else:
            data_dict = data
            
        if sum(data_dict.values()) == 0:
            return None
            
        fig, ax = plt.subplots(figsize=(6, 6))
        
        labels = list(data_dict.keys())
        sizes = list(data_dict.values())
        
        colors_list = plt.cm.Set3(range(len(labels)))
        
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors_list)
        ax.set_title(title)
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    def create_bar_chart(self, data_dict, title="Comparison", xlabel="Category", ylabel="Count"):
        """Create a bar chart from dictionary data"""
        if not data_dict:
            return None
            
        fig, ax = plt.subplots(figsize=(8, 5))
        
        categories = list(data_dict.keys())
        values = list(data_dict.values())
        
        bars = ax.bar(categories, values, color='steelblue', alpha=0.7)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom')
        
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
