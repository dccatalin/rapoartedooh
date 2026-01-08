import json
import os

class CompanySettings:
    """
    Manages company settings (name, address, logo).
    Saves to data/company_settings.json
    """
    def __init__(self):
        self.storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'company_settings.json')
        
    def get_settings(self):
        """Get company settings"""
        try:
            if not os.path.exists(self.storage_path):
                return {}
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading company settings: {e}")
            return {}
            
    def save_settings(self, **kwargs):
        """Save company settings by merging with existing ones"""
        data = self.get_settings()
        data.update(kwargs)
        
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving company settings: {e}")
            return False
