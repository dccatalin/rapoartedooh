"""
Fleet Utilization Report Generator
Generates reports on vehicle and driver utilization.
"""
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
import datetime
from src.reporting.report_generator import ReportGenerator
from src.data.campaign_storage import CampaignStorage
from src.data.vehicle_manager import VehicleManager
from src.data.driver_manager import DriverManager

class FleetUtilizationReportGenerator(ReportGenerator):
    """Generate fleet utilization and performance reports"""
    
    def __init__(self):
        super().__init__(data_manager=None)
        self.storage = CampaignStorage()
        self.vehicle_manager = VehicleManager()
        self.driver_manager = DriverManager()
        
    def generate_vehicle_utilization_report(self, start_date: datetime.date, 
                                            end_date: datetime.date, 
                                            output_path: str = None):
        """Generate vehicle utilization report for a date range"""
        if output_path is None:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self._get_report_path(f"vehicle_utilization_{timestamp}.pdf")
            
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        
        # Title
        story.append(Paragraph("RAPORT UTILIZARE FLOTA", self.styles['Title']))
        story.append(Spacer(1, 12))
        
        # Period
        period_text = f"Perioada: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
        story.append(Paragraph(period_text, self.styles['Heading2']))
        story.append(Spacer(1, 24))
        
        # Get all vehicles and campaigns
        vehicles = self.vehicle_manager.get_all_vehicles()
        campaigns = self.storage.get_all_campaigns()
        
        # Calculate utilization for each vehicle
        total_days = (end_date - start_date).days + 1
        
        utilization_data = []
        
        for vehicle in vehicles:
            vehicle_id = vehicle['id']
            vehicle_name = vehicle['name']
            registration = vehicle.get('registration', '')
            driver_name = vehicle.get('driver_name', 'Neasignat')
            
            # Find campaigns for this vehicle in date range
            vehicle_campaigns = [
                c for c in campaigns 
                if c.get('vehicle_id') == vehicle_id and 
                self._campaign_in_range(c, start_date, end_date)
            ]
            
            # Calculate days used
            days_used = self._calculate_days_used(vehicle_campaigns, start_date, end_date)
            utilization_pct = (days_used / total_days * 100) if total_days > 0 else 0
            
            utilization_data.append({
                'vehicle': f"{vehicle_name} ({registration})",
                'driver': driver_name,
                'campaigns': len(vehicle_campaigns),
                'days_used': days_used,
                'utilization': utilization_pct
            })
            
        # Sort by utilization descending
        utilization_data.sort(key=lambda x: x['utilization'], reverse=True)
        
        # Create table
        table_data = [
            ['Vehicul', 'Sofer', 'Campanii', 'Zile Utilizate', 'Utilizare (%)']
        ]
        
        for data in utilization_data:
            table_data.append([
                data['vehicle'],
                data['driver'],
                str(data['campaigns']),
                f"{data['days_used']} / {total_days}",
                f"{data['utilization']:.1f}%"
            ])
            
        t = Table(table_data, colWidths=[2*inch, 1.5*inch, 1*inch, 1.2*inch, 1*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(t)
        story.append(Spacer(1, 24))
        
        # Summary statistics
        if utilization_data:
            avg_utilization = sum(d['utilization'] for d in utilization_data) / len(utilization_data)
            total_campaigns = sum(d['campaigns'] for d in utilization_data)
            
            story.append(Paragraph("Statistici Generale", self.styles['Heading2']))
            story.append(Spacer(1, 12))
            
            summary_data = [
                ['Total Vehicule', str(len(vehicles))],
                ['Total Campanii', str(total_campaigns)],
                ['Utilizare Medie', f"{avg_utilization:.1f}%"],
                ['Perioada Analiza', f"{total_days} zile"]
            ]
            
            summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(summary_table)
            
        doc.build(story)
        self._open_report(output_path)
        return output_path
        
    def generate_driver_performance_report(self, start_date: datetime.date, 
                                           end_date: datetime.date,
                                           output_path: str = None):
        """Generate driver performance report"""
        if output_path is None:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self._get_report_path(f"driver_performance_{timestamp}.pdf")
            
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        
        # Title
        story.append(Paragraph("RAPORT PERFORMANTA SOFERI", self.styles['Title']))
        story.append(Spacer(1, 12))
        
        # Period
        period_text = f"Perioada: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
        story.append(Paragraph(period_text, self.styles['Heading2']))
        story.append(Spacer(1, 24))
        
        # Get all drivers and campaigns
        drivers = self.driver_manager.get_all_drivers()
        campaigns = self.storage.get_all_campaigns()
        
        performance_data = []
        
        for driver in drivers:
            driver_id = driver['id']
            driver_name = driver['name']
            
            # Find campaigns for this driver
            driver_campaigns = [
                c for c in campaigns 
                if c.get('driver_id') == driver_id and 
                self._campaign_in_range(c, start_date, end_date)
            ]
            
            # Calculate metrics
            total_campaigns = len(driver_campaigns)
            total_km = sum(c.get('known_distance_total', 0) for c in driver_campaigns)
            
            # Get unique clients
            clients = set(c.get('client_name') for c in driver_campaigns if c.get('client_name'))
            
            performance_data.append({
                'driver': driver_name,
                'campaigns': total_campaigns,
                'clients': len(clients),
                'total_km': total_km
            })
            
        # Sort by campaigns descending
        performance_data.sort(key=lambda x: x['campaigns'], reverse=True)
        
        # Create table
        table_data = [
            ['Sofer', 'Campanii', 'Clienti Unici', 'Total KM']
        ]
        
        for data in performance_data:
            table_data.append([
                data['driver'],
                str(data['campaigns']),
                str(data['clients']),
                f"{data['total_km']:,} km"
            ])
            
        t = Table(table_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(t)
        
        doc.build(story)
        self._open_report(output_path)
        return output_path
        
    def _campaign_in_range(self, campaign: dict, start_date: datetime.date, 
                           end_date: datetime.date) -> bool:
        """Check if campaign overlaps with date range"""
        try:
            c_start = datetime.date.fromisoformat(str(campaign['start_date']))
            c_end = datetime.date.fromisoformat(str(campaign['end_date']))
            return c_start <= end_date and c_end >= start_date
        except:
            return False
            
    def _calculate_days_used(self, campaigns: list, start_date: datetime.date, 
                            end_date: datetime.date) -> int:
        """Calculate total unique days used by campaigns"""
        used_days = set()
        
        for campaign in campaigns:
            try:
                c_start = datetime.date.fromisoformat(str(campaign['start_date']))
                c_end = datetime.date.fromisoformat(str(campaign['end_date']))
                
                # Clip to analysis range
                actual_start = max(c_start, start_date)
                actual_end = min(c_end, end_date)
                
                # Add all days in range
                current = actual_start
                while current <= actual_end:
                    used_days.add(current)
                    current += datetime.timedelta(days=1)
            except:
                continue
                
        return len(used_days)
