import json
import os

class CityDataManager:
    def __init__(self):
        self.profiles_path = os.path.join(os.path.dirname(__file__), 'city_data_history.json')
        self.events_path = os.path.join(os.path.dirname(__file__), 'special_events.json')
        self.profiles = self._load_profiles()
        self.special_events = self._load_special_events()

    def _load_profiles(self):
        if not os.path.exists(self.profiles_path):
            return {}
        try:
            with open(self.profiles_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading city profiles: {e}")
            return {}

    def _load_special_events(self):
        if not os.path.exists(self.events_path):
            return {}
        try:
            with open(self.events_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading special events: {e}")
            return {}

    def get_event_multipliers(self, city_name, date_obj):
        """
        Get traffic and pedestrian multipliers for a specific city and date.
        Supports both legacy single-date events and new date-range events.
        Returns (traffic_mult, pedestrian_mult, event_name)
        Defaults to (1.0, 1.0, None) if no event found.
        """
        if not city_name or not date_obj:
            return 1.0, 1.0, None
            
        # Normalize city name
        search_name = city_name.lower().strip()
        city_events = None
        
        # Find city in events
        for name, events in self.special_events.items():
            if name.lower() == search_name:
                city_events = events
                break
                
        if not city_events:
            return 1.0, 1.0, None
            
        date_str = date_obj.strftime('%Y-%m-%d')
        
        # Check for events that apply to this date
        for event_key, event in city_events.items():
            # New format: check date range
            if 'start_date' in event:
                import datetime
                start_date = datetime.datetime.strptime(event['start_date'], '%Y-%m-%d').date()
                end_date = datetime.datetime.strptime(event['end_date'], '%Y-%m-%d').date()
                
                if start_date <= date_obj <= end_date:
                    return (
                        event.get('traffic_multiplier', 1.0),
                        event.get('pedestrian_multiplier', 1.0),
                        event.get('name')
                    )
            # Legacy format: single date as key
            elif event_key == date_str:
                return (
                    event.get('traffic_multiplier', 1.0),
                    event.get('pedestrian_multiplier', 1.0),
                    event.get('name')
                )
            
        return 1.0, 1.0, None


    def get_city_profile(self, city_name):
        """Get current profile for a specific city (case insensitive search)"""
        # Normalize search
        search_name = city_name.lower().strip()
        
        city_data = None
        real_name = None
        
        # Direct match
        if city_name in self.profiles:
            city_data = self.profiles[city_name]
            real_name = city_name
        else:
            # Case insensitive match
            for name, profile in self.profiles.items():
                if name.lower() == search_name:
                    city_data = profile
                    real_name = name
                    break
            
            # Partial match if not found
            if not city_data:
                for name, profile in self.profiles.items():
                    if search_name in name.lower():
                        city_data = profile
                        real_name = name
                        break
        
        if city_data:
            # Return data for current reference period
            current_ref = city_data.get('current', {}).get('ref')
            if current_ref and current_ref in city_data:
                return city_data[current_ref]
            
            # Fallback: return first key that looks like a period or just the first key
            for key in city_data:
                if key != 'current':
                    return city_data[key]
                    
        return None

    def get_city_data_for_period(self, city_name, target_date):
        """
        Get city data for a specific date/period.
        Finds the historical entry that covers the target_date.
        If no exact match, falls back to the closest available data.
        """
        import datetime
        
        # Get full history for the city
        # We need to access the raw profile dictionary, not just the current one
        search_name = city_name.lower().strip()
        history = None
        
        if city_name in self.profiles:
            history = self.profiles[city_name]
        else:
            for name, profile in self.profiles.items():
                if name.lower() == search_name:
                    history = profile
                    break
            if not history:
                for name, profile in self.profiles.items():
                    if search_name in name.lower():
                        history = profile
                        break
        
        if not history:
            return None
            
        # Convert target_date to comparable format (YYYY-Qx)
        if isinstance(target_date, datetime.date):
            target_year = target_date.year
            target_quarter = (target_date.month - 1) // 3 + 1
        else:
            # Assume it's already a date object or similar
            try:
                target_year = target_date.year
                target_quarter = (target_date.month - 1) // 3 + 1
            except:
                # Fallback to current
                now = datetime.datetime.now()
                target_year = now.year
                target_quarter = (now.month - 1) // 3 + 1
                
        target_key = f"{target_year}-Q{target_quarter}"
        
        # 1. Try exact match
        if target_key in history:
            return history[target_key]
            
        # 2. Find closest available period
        available_periods = [k for k in history.keys() if k != 'current']
        if not available_periods:
            return None
            
        # Sort periods
        available_periods.sort()
        
        # Find closest
        # For now, just return the most recent one that is <= target_key
        # If target is older than all, return oldest. If newer than all, return newest.
        
        best_match = available_periods[-1] # Default to newest
        
        for period in reversed(available_periods):
            if period <= target_key:
                best_match = period
                break
                
        return history[best_match]

    def get_all_cities(self):
        return list(self.profiles.keys())
    
    def extrapolate_city_data(self, city_name, population):
        """
        Extrapolate city data based on population using similar-sized cities as reference.
        Uses linear interpolation between closest population matches.
        """
        if not population or population <= 0:
            return None
            
        # Get all cities sorted by population (using current data)
        cities_by_pop = []
        for name, history in self.profiles.items():
            # Extract current data
            current_ref = history.get('current', {}).get('ref')
            if current_ref and current_ref in history:
                data = history[current_ref]
                if 'population' in data:
                    cities_by_pop.append((name, data))
        
        cities_by_pop.sort(key=lambda x: x[1]['population'])
        
        # Find closest cities by population
        smaller_city = None
        larger_city = None
        
        for name, data in cities_by_pop:
            if data['population'] <= population:
                smaller_city = (name, data)
            elif data['population'] > population and larger_city is None:
                larger_city = (name, data)
                break
        
        # If exact match or outside range, use closest
        if smaller_city and not larger_city:
            # Larger than all cities - use largest as template
            template = smaller_city[1]
        elif larger_city and not smaller_city:
            # Smaller than all cities - use smallest as template
            template = larger_city[1]
        elif smaller_city and larger_city:
            # Interpolate between two cities
            s_pop = smaller_city[1]['population']
            l_pop = larger_city[1]['population']
            ratio = (population - s_pop) / (l_pop - s_pop) if l_pop != s_pop else 0.5
            
            # Interpolate numeric values
            template = {
                'population': population,
                'active_population_pct': int(
                    smaller_city[1]['active_population_pct'] * (1 - ratio) +
                    larger_city[1]['active_population_pct'] * ratio
                ),
                'daily_traffic_total': int(
                    smaller_city[1]['daily_traffic_total'] * (1 - ratio) +
                    larger_city[1]['daily_traffic_total'] * ratio
                ),
                'daily_pedestrian_total': int(
                    smaller_city[1]['daily_pedestrian_total'] * (1 - ratio) +
                    larger_city[1]['daily_pedestrian_total'] * ratio
                ),
                'modal_split': {
                    'auto': int(
                        smaller_city[1]['modal_split']['auto'] * (1 - ratio) +
                        larger_city[1]['modal_split']['auto'] * ratio
                    ),
                    'walking': int(
                        smaller_city[1]['modal_split']['walking'] * (1 - ratio) +
                        larger_city[1]['modal_split']['walking'] * ratio
                    ),
                    'cycling': int(
                        smaller_city[1]['modal_split']['cycling'] * (1 - ratio) +
                        larger_city[1]['modal_split']['cycling'] * ratio
                    ),
                    'public_transport': int(
                        smaller_city[1]['modal_split']['public_transport'] * (1 - ratio) +
                        larger_city[1]['modal_split']['public_transport'] * ratio
                    )
                },
                'avg_commute_distance_km': int(
                    smaller_city[1]['avg_commute_distance_km'] * (1 - ratio) +
                    larger_city[1]['avg_commute_distance_km'] * ratio
                ),
                'description': f"Date extrapolate bazate pe populatia de {population:,} locuitori."
            }
            return template
        else:
            # No reference cities - use defaults
            template = {
                'population': population,
                'active_population_pct': 58,
                'daily_traffic_total': int(population * 0.5),
                'daily_pedestrian_total': int(population * 0.6),
                'modal_split': {
                    'auto': 35,
                    'walking': 27,
                    'cycling': 4,
                    'public_transport': 34
                },
                'avg_commute_distance_km': 8,
                'description': f"Date extrapolate bazate pe populatia de {population:,} locuitori."
            }
        
        return template
    
    def refresh_city_data(self, city_name, force=False):
        """
        Fetch fresh data from public sources and update the city profile.
        Respects update_preference unless force=True.
        Returns dict with 'success', 'data', 'source', 'needs_confirmation' keys.
        """
        from src.data.data_fetcher import DataFetcher
        
        # Check update preference
        preference = self.get_update_preference(city_name)
        
        # If manual and not forced, return that confirmation is needed
        if preference == 'manual' and not force:
            return {
                'success': False,
                'needs_confirmation': True,
                'message': 'Manual update preference - confirmation required'
            }
        
        # Try to fetch based on preference
        fetcher = DataFetcher()
        new_data = None
        source = None
        
        if preference == 'ins':
            # Try INS first (placeholder for now)
            new_data = fetcher.fetch_from_ins(city_name)
            source = 'INS'
            if not new_data:
                # Fallback to public if INS fails
                new_data = fetcher.fetch_city_data(city_name)
                source = 'Public'
        elif preference == 'brat':
            # Try BRAT first (placeholder for now)
            new_data = fetcher.fetch_from_brat(city_name)
            source = 'BRAT'
            if not new_data:
                # Fallback to public if BRAT fails
                new_data = fetcher.fetch_city_data(city_name)
                source = 'Public'
        else:  # public or manual with force=True
            new_data = fetcher.fetch_city_data(city_name)
            source = 'Public'
        
        if new_data:
            # Get current profile to preserve other fields
            current_profile = self.get_city_profile(city_name)
            if not current_profile:
                # If new city, extrapolate first to get base structure
                if 'population' in new_data:
                    current_profile = self.extrapolate_city_data(city_name, new_data['population'])
                else:
                    return {
                        'success': False,
                        'message': 'Could not create base profile'
                    }
            
            # Update fields
            current_profile.update(new_data)
            current_profile['source'] = source
            
            # Save using add_city logic (handles history)
            self.add_city(city_name, current_profile)
            
            return {
                'success': True,
                'data': current_profile,
                'source': source
            }
            
        return {
            'success': False,
            'message': 'Could not fetch data from any source'
        }

    def add_city(self, city_name, city_data):
        """Add a new city to the profiles and save to file in historical format"""
        import datetime
        
        # Determine current quarter
        now = datetime.datetime.now()
        quarter = (now.month - 1) // 3 + 1
        period_key = f"{now.year}-Q{quarter}"
        
        # Add metadata
        city_data['last_updated'] = now.isoformat()
        city_data['source'] = city_data.get('source', "User Input / Extrapolation")
        city_data['update_preference'] = city_data.get('update_preference', 'public')  # Default to public updates
        
        # Create historical structure
        if city_name not in self.profiles:
            self.profiles[city_name] = {}
            
        self.profiles[city_name][period_key] = city_data
        self.profiles[city_name]['current'] = {'ref': period_key}
        
        self._save_profiles()
    
    def get_update_preference(self, city_name):
        """Get the update preference for a city"""
        profile = self.get_city_profile(city_name)
        if profile:
            return profile.get('update_preference', 'public')
        return 'public'
    
    def set_update_preference(self, city_name, preference):
        """Set the update preference for a city (public/ins/brat/manual)"""
        if preference not in ['public', 'ins', 'brat', 'manual']:
            return False
            
        # Get the city's current period data
        search_name = city_name.lower().strip()
        city_history = None
        real_name = None
        
        if city_name in self.profiles:
            city_history = self.profiles[city_name]
            real_name = city_name
        else:
            for name, profile in self.profiles.items():
                if name.lower() == search_name:
                    city_history = profile
                    real_name = name
                    break
        
        if not city_history:
            return False
        
        # Update preference in current period
        current_ref = city_history.get('current', {}).get('ref')
        if current_ref and current_ref in city_history:
            city_history[current_ref]['update_preference'] = preference
            self._save_profiles()
            return True
            
        return False
        
    def _save_profiles(self):
        """Save profiles to JSON file"""
        try:
            with open(self.profiles_path, 'w', encoding='utf-8') as f:
                json.dump(self.profiles, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Error saving city profiles: {e}")
            return False

    def _save_special_events(self):
        """Save special events to JSON file"""
        try:
            with open(self.events_path, 'w', encoding='utf-8') as f:
                json.dump(self.special_events, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Error saving special events: {e}")
            return False
