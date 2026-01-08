"""
Data validation utilities for campaign inputs.
Validates dates, hours, speeds, distances, and other campaign parameters.
"""
import datetime
import re
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of a validation check"""
    def __init__(self, is_valid: bool, message: str = "", severity: str = "info"):
        self.is_valid = is_valid
        self.message = message
        self.severity = severity  # "info", "warning", "error"


class CampaignValidator:
    """Validates campaign input data"""
    
    @staticmethod
    def validate_date_range(start_date: datetime.date, end_date: datetime.date) -> ValidationResult:
        """Validate campaign date range"""
        if start_date > end_date:
            return ValidationResult(False, "Start date must be before end date", "error")
        
        # Check if dates are in the past
        today = datetime.date.today()
        if end_date < today:
            return ValidationResult(True, "Campaign dates are in the past", "warning")
        
        # Check if campaign is too long
        duration = (end_date - start_date).days
        if duration > 365:
            return ValidationResult(True, f"Campaign duration is very long ({duration} days)", "warning")
        
        if duration < 1:
            return ValidationResult(False, "Campaign must be at least 1 day", "error")
        
        return ValidationResult(True, f"Campaign duration: {duration} days", "info")
    
    @staticmethod
    def validate_hours(hours_str: str) -> ValidationResult:
        """Validate hours format (HH:MM-HH:MM)"""
        pattern = r'^\d{1,2}:\d{2}-\d{1,2}:\d{2}$'
        if not re.match(pattern, hours_str):
            return ValidationResult(False, "Invalid format. Use HH:MM-HH:MM (e.g., 09:00-18:00)", "error")
        
        try:
            start, end = hours_str.split('-')
            start_h, start_m = map(int, start.split(':'))
            end_h, end_m = map(int, end.split(':'))
            
            if not (0 <= start_h < 24 and 0 <= start_m < 60):
                return ValidationResult(False, "Invalid start time", "error")
            
            if not (0 <= end_h < 24 and 0 <= end_m < 60):
                return ValidationResult(False, "Invalid end time", "error")
            
            # Calculate duration
            start_mins = start_h * 60 + start_m
            end_mins = end_h * 60 + end_m
            
            if end_mins <= start_mins:
                return ValidationResult(False, "End time must be after start time", "error")
            
            duration_hours = (end_mins - start_mins) / 60
            
            if duration_hours < 1:
                return ValidationResult(True, f"Very short campaign hours ({duration_hours:.1f}h)", "warning")
            
            return ValidationResult(True, f"Daily duration: {duration_hours:.1f} hours", "info")
            
        except Exception as e:
            logger.error(f"Error validating hours: {e}")
            return ValidationResult(False, "Invalid time format", "error")
    
    @staticmethod
    def validate_speed(speed_kmh: float) -> ValidationResult:
        """Validate vehicle speed"""
        if speed_kmh < 0:
            return ValidationResult(False, "Speed cannot be negative", "error")
        
        if speed_kmh < 5:
            return ValidationResult(True, f"Very low speed ({speed_kmh} km/h). Is this correct?", "warning")
        
        if speed_kmh > 80:
            return ValidationResult(True, f"Very high speed ({speed_kmh} km/h) for urban DOOH", "warning")
        
        if 20 <= speed_kmh <= 40:
            return ValidationResult(True, f"Optimal urban speed ({speed_kmh} km/h)", "info")
        
        return ValidationResult(True, f"Speed: {speed_kmh} km/h", "info")
    
    @staticmethod
    def validate_distance(distance_km: float, campaign_days: int) -> ValidationResult:
        """Validate campaign distance"""
        if distance_km < 0:
            return ValidationResult(False, "Distance cannot be negative", "error")
        
        if distance_km == 0:
            return ValidationResult(False, "Distance must be greater than 0", "error")
        
        daily_km = distance_km / campaign_days if campaign_days > 0 else 0
        
        if daily_km < 10:
            return ValidationResult(True, f"Low daily distance ({daily_km:.1f} km/day)", "warning")
        
        if daily_km > 500:
            return ValidationResult(True, f"Very high daily distance ({daily_km:.1f} km/day)", "warning")
        
        return ValidationResult(True, f"Daily average: {daily_km:.1f} km", "info")
    
    @staticmethod
    def validate_population(population: int) -> ValidationResult:
        """Validate city population"""
        if population < 0:
            return ValidationResult(False, "Population cannot be negative", "error")
        
        if population < 1000:
            return ValidationResult(True, "Very small city population", "warning")
        
        if population > 10000000:
            return ValidationResult(True, "Very large city population", "warning")
        
        return ValidationResult(True, f"Population: {population:,}", "info")
    
    @staticmethod
    def validate_stationing(stationing_min: int, daily_hours: float) -> ValidationResult:
        """Validate stationing time"""
        if stationing_min < 0:
            return ValidationResult(False, "Stationing time cannot be negative", "error")
        
        if stationing_min > 60:
            return ValidationResult(True, "Stationing time exceeds 1 hour per hour", "warning")
        
        if stationing_min == 0:
            return ValidationResult(True, "No stationing time (continuous movement)", "info")
        
        # Check if stationing makes sense with daily hours
        total_stationing_hours = (stationing_min / 60) * daily_hours
        if total_stationing_hours > daily_hours * 0.8:
            return ValidationResult(True, "High stationing time (>80% of campaign hours)", "warning")
        
        return ValidationResult(True, f"Stationing: {stationing_min} min/hour", "info")
    
    @staticmethod
    def validate_costs(cost_per_km: float, fixed_costs: float, revenue: float) -> ValidationResult:
        """Validate financial inputs"""
        if cost_per_km < 0 or fixed_costs < 0 or revenue < 0:
            return ValidationResult(False, "Costs and revenue cannot be negative", "error")
        
        if cost_per_km == 0 and fixed_costs == 0 and revenue == 0:
            return ValidationResult(True, "No financial data entered", "info")
        
        if revenue > 0 and (cost_per_km + fixed_costs) == 0:
            return ValidationResult(True, "Revenue entered but no costs specified", "warning")
        
        if (cost_per_km + fixed_costs) > 0 and revenue == 0:
            return ValidationResult(True, "Costs entered but no revenue specified", "warning")
        
        return ValidationResult(True, "Financial data looks valid", "info")
