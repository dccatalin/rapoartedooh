"""
Financial Report Generator
Generates dedicated financial PDF reports with cost breakdowns and ROI metrics.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
import datetime
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class FinancialReportGenerator:
    """Generate financial PDF reports for campaigns"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self) -> None:
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='FinancialTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1976D2'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#424242'),
            spaceBefore=20,
            spaceAfter=12
        ))
    
    def generate_financial_report(
        self, 
        campaign_data: Dict[str, Any], 
        output_path: str,
        impressions_total: int = 0
    ) -> bool:
        """Generate financial PDF report"""
        try:
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            story = []
            
            # Title
            title = Paragraph("Financial Report", self.styles['FinancialTitle'])
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Campaign Info
            campaign_name = campaign_data.get('campaign_name', 'Untitled')
            client_name = campaign_data.get('client_name', 'Unknown')
            
            info_text = f"<b>Campaign:</b> {campaign_name}<br/><b>Client:</b> {client_name}"
            story.append(Paragraph(info_text, self.styles['Normal']))
            story.append(Spacer(1, 24))
            
            # Financial Summary
            story.append(Paragraph("Financial Summary", self.styles['SectionHeader']))
            
            cost_per_km = campaign_data.get('cost_per_km', 0)
            fixed_costs = campaign_data.get('fixed_costs', 0)
            revenue = campaign_data.get('expected_revenue', 0)
            
            # Use calculated distance if available, otherwise use known_distance_total
            distance = campaign_data.get('calculated_distance', 0)
            if not distance:
                distance = campaign_data.get('known_distance_total', 0) or 0
            
            total_cost = (distance * cost_per_km) + fixed_costs
            profit = revenue - total_cost
            roi = ((profit / total_cost) * 100) if total_cost > 0 else 0
            
            # Summary Table
            summary_data = [
                ['Metric', 'Value'],
                ['Distance', f'{distance:,.1f} km'],
                ['Cost per km', f'{cost_per_km:,.2f} €'],
                ['Variable Costs', f'{distance * cost_per_km:,.2f} €'],
                ['Fixed Costs', f'{fixed_costs:,.2f} €'],
                ['Total Cost', f'{total_cost:,.2f} €'],
                ['Expected Revenue', f'{revenue:,.2f} €'],
                ['Profit/Loss', f'{profit:,.2f} €'],
                ['ROI', f'{roi:,.1f}%']
            ]
            
            if impressions_total > 0:
                cost_per_impression = (total_cost / impressions_total) if impressions_total > 0 else 0
                summary_data.append(['Cost per Impression', f'{cost_per_impression:.4f} €'])
            
            summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -2), (-1, -1), 11),
            ]))
            
            story.append(summary_table)
            story.append(Spacer(1, 24))
            
            # Cost Breakdown Pie Chart
            if total_cost > 0:
                story.append(Paragraph("Cost Breakdown", self.styles['SectionHeader']))
                
                pie_chart = self._create_cost_pie_chart(
                    distance * cost_per_km,
                    fixed_costs
                )
                story.append(pie_chart)
                story.append(Spacer(1, 24))
            
            # Revenue vs Cost Chart
            if revenue > 0:
                story.append(Paragraph("Revenue vs Cost", self.styles['SectionHeader']))
                
                bar_chart = self._create_revenue_cost_chart(revenue, total_cost)
                story.append(bar_chart)
                story.append(Spacer(1, 24))
            
            # ROI Analysis
            story.append(Paragraph("ROI Analysis", self.styles['SectionHeader']))
            
            roi_color = "green" if roi > 0 else "red" if roi < 0 else "orange"
            roi_text = f"""
            <para align=center>
            <font size=14>
            The campaign shows a <font color={roi_color}><b>{roi:,.1f}%</b></font> ROI.<br/>
            {'This is a <b>profitable</b> campaign.' if roi > 0 else 'This campaign is <b>not profitable</b>.' if roi < 0 else 'This campaign <b>breaks even</b>.'}
            </font>
            </para>
            """
            story.append(Paragraph(roi_text, self.styles['Normal']))
            
            # Build PDF
            doc.build(story)
            logger.info(f"Financial report generated: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating financial report: {e}")
            return False
    
    def _create_cost_pie_chart(
        self, 
        variable_costs: float, 
        fixed_costs: float
    ) -> Drawing:
        """Create pie chart for cost breakdown"""
        drawing = Drawing(400, 200)
        
        pie = Pie()
        pie.x = 150
        pie.y = 50
        pie.width = 100
        pie.height = 100
        
        pie.data = [variable_costs, fixed_costs]
        pie.labels = ['Variable Costs', 'Fixed Costs']
        pie.slices.strokeWidth = 0.5
        pie.slices[0].fillColor = colors.HexColor('#2196F3')
        pie.slices[1].fillColor = colors.HexColor('#FF9800')
        
        drawing.add(pie)
        return drawing
    
    def _create_revenue_cost_chart(
        self, 
        revenue: float, 
        cost: float
    ) -> Drawing:
        """Create bar chart for revenue vs cost"""
        drawing = Drawing(400, 200)
        
        chart = VerticalBarChart()
        chart.x = 50
        chart.y = 50
        chart.height = 125
        chart.width = 300
        chart.data = [[revenue, cost]]
        chart.categoryAxis.categoryNames = ['Revenue', 'Cost']
        chart.valueAxis.valueMin = 0
        chart.valueAxis.valueMax = max(revenue, cost) * 1.2
        chart.bars[0].fillColor = colors.HexColor('#4CAF50')
        chart.bars[1].fillColor = colors.HexColor('#F44336')
        
        drawing.add(chart)
        return drawing
