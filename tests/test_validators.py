import pytest
from datetime import date, timedelta
from src.utils.validators import CampaignValidator

class TestCampaignValidator:
    def setup_method(self):
        self.validator = CampaignValidator()

    def test_validate_date_range(self):
        today = date.today()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)
        
        # Valid range
        assert self.validator.validate_date_range(today, tomorrow).is_valid
        
        # Invalid range (end before start)
        assert not self.validator.validate_date_range(tomorrow, today).is_valid
        
        # Warning (entire campaign in past)
        past_start = today - timedelta(days=10)
        past_end = today - timedelta(days=5)
        result = self.validator.validate_date_range(past_start, past_end)
        assert result.is_valid
        assert result.severity == "warning"

    def test_validate_hours(self):
        # Valid hours
        assert self.validator.validate_hours("09:00-17:00").is_valid
        assert self.validator.validate_hours("00:00-23:59").is_valid
        
        # Invalid format
        assert not self.validator.validate_hours("9-5").is_valid
        assert not self.validator.validate_hours("invalid").is_valid
        
        # Invalid logic
        assert not self.validator.validate_hours("17:00-09:00").is_valid  # End before start
        assert not self.validator.validate_hours("25:00-26:00").is_valid  # Invalid time

    def test_validate_costs(self):
        # Valid financials
        assert self.validator.validate_costs(1.5, 100, 1000).is_valid
        
        # Invalid negatives
        assert not self.validator.validate_costs(-1, 100, 1000).is_valid
        assert not self.validator.validate_costs(1.5, -100, 1000).is_valid
        
        # Warning (low revenue)
        # Note: Logic in validator is: if revenue > 0 and costs > 0 and revenue < costs -> warning?
        # Actually checking code: 
        # if (cost_per_km + fixed_costs) > 0 and revenue == 0: warning
        # if revenue > 0 and (cost_per_km + fixed_costs) == 0: warning
        
        result = self.validator.validate_costs(1.0, 100, 0) # Costs but no revenue
        assert result.is_valid
        assert result.severity == "warning"
