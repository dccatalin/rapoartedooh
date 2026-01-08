import requests
from bs4 import BeautifulSoup
import re
import datetime
import json
import os
import time

class DataFetcher:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.cache_path = os.path.join(os.path.dirname(__file__), 'fetch_cache.json')
        self.cache_expiry_days = 30

    def fetch_city_data(self, city_name):
        """
        Fetch city data from public sources with caching.
        Tries: Cache -> INS -> OSM -> Wikipedia
        """
        print(f"Fetching data for {city_name}...")
        
        # Check cache first
        cached = self._get_cached_data(city_name)
        if cached:
            print(f"Using cached data for {city_name}")
            return cached
        
        data = {}
        
        # Try INS (official Romanian statistics)
        ins_data = self._fetch_from_ins(city_name)
        if ins_data:
            data.update(ins_data)
            data['source'] = 'INS'
        
        # Try OpenStreetMap for POI and road data
        osm_data = self._fetch_from_osm(city_name)
        if osm_data:
            data.update(osm_data)
            if 'source' not in data:
                data['source'] = 'OpenStreetMap'
        
        # Fallback to Wikipedia if no official data
        if not data or 'population' not in data:
            wiki_data = self._fetch_from_wikipedia(city_name)
            if wiki_data:
                data.update(wiki_data)
                if 'source' not in data:
                    data['source'] = 'Wikipedia'
        
        # Estimate traffic if we have population
        if 'population' in data:
            traffic_data = self._estimate_traffic(data)
            data.update(traffic_data)
        
        if data:
            data['last_updated'] = datetime.datetime.now().isoformat()
            self._save_to_cache(city_name, data)
            
        return data

    def _fetch_from_wikipedia(self, city_name):
        """Scrape population from Wikipedia infobox"""
        try:
            # Construct URL (Romanian Wikipedia)
            url = f"https://ro.wikipedia.org/wiki/{city_name}"
            response = requests.get(url, headers=self.headers, timeout=5)
            
            if response.status_code != 200:
                # Try with "Municipiul" prefix if simple name fails
                url = f"https://ro.wikipedia.org/wiki/Municipiul_{city_name}"
                response = requests.get(url, headers=self.headers, timeout=5)
                if response.status_code != 200:
                    return None

            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find infobox
            infobox = soup.find('table', {'class': 'infobox'})
            if not infobox:
                return None
                
            data = {}
            
            # Extract Population
            # Look for rows containing "Populație"
            for row in infobox.find_all('tr'):
                header = row.find('th')
                if header and 'Populație' in header.text:
                    # The value might be in this row or next rows
                    # Usually in Wikipedia infoboxes, it's complex. 
                    # Let's look for the cell with the number
                    cell = row.find('td')
                    if not cell:
                        # Check next row
                        next_row = row.find_next_sibling('tr')
                        if next_row:
                            cell = next_row.find('td')
                    
                    if cell:
                        text = cell.text.strip()
                        # Extract number (remove references like [1], spaces, etc)
                        # Regex to find the first large number
                        match = re.search(r'(\d[\d\s\.]+\d)', text)
                        if match:
                            num_str = match.group(1).replace('.', '').replace(' ', '').replace('\xa0', '')
                            try:
                                data['population'] = int(num_str)
                            except ValueError:
                                pass
                    break
            
            return data
            
        except Exception as e:
            print(f"Error fetching from Wikipedia: {e}")
            return None

    def _fetch_from_ins(self, city_name):
        """Fetch population from INS (Institutul National de Statistica)"""
        try:
            # INS Tempo Online API endpoint
            # Note: This is a simplified example. Real INS API may require different parameters
            url = "http://statistici.insse.ro:8077/tempo-online/"
            
            # For now, return None as INS API requires complex authentication
            # This is a placeholder for future implementation
            print(f"INS API not fully implemented yet for {city_name}")
            return None
            
        except Exception as e:
            print(f"Error fetching from INS: {e}")
            return None
    
    def _fetch_from_osm(self, city_name):
        """Fetch POI and road data from OpenStreetMap Overpass API"""
        try:
            # Overpass API endpoint
            url = "https://overpass-api.de/api/interpreter"
            
            # Query for POI count and road network in city
            query = f"""
            [out:json][timeout:10];
            area["name"="{city_name}"]["admin_level"~"^(6|8)$"]->.city;
            (
              node(area.city)["amenity"];
              way(area.city)["highway"];
            );
            out count;
            """
            
            response = requests.post(url, data={'data': query}, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                # Extract counts from tags
                data = {}
                
                # This is simplified - real implementation would parse the response better
                if 'elements' in result:
                    data['osm_poi_count'] = len([e for e in result['elements'] if e.get('type') == 'node'])
                    data['osm_road_count'] = len([e for e in result['elements'] if e.get('type') == 'way'])
                
                return data
            
            # Rate limiting: wait 0.5s between requests
            time.sleep(0.5)
            return None
            
        except Exception as e:
            print(f"Error fetching from OSM: {e}")
            return None
    
    def _estimate_traffic(self, data):
        """Estimate traffic based on population and other factors"""
        population = data.get('population', 0)
        if population == 0:
            return {}
        
        # Simple estimation formulas (can be refined)
        # Assume 30-40% of population generates daily traffic
        daily_traffic_total = int(population * 0.35)
        
        # Pedestrian traffic: ~25% of population
        daily_pedestrian_total = int(population * 0.25)
        
        # Active population percentage (working age)
        active_population_pct = 60
        
        return {
            'daily_traffic_total': daily_traffic_total,
            'daily_pedestrian_total': daily_pedestrian_total,
            'active_population_pct': active_population_pct
        }
    
    def _get_cached_data(self, city_name):
        """Get cached data if available and not expired"""
        try:
            if not os.path.exists(self.cache_path):
                return None
            
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            
            if city_name not in cache:
                return None
            
            cached_entry = cache[city_name]
            timestamp = datetime.datetime.fromisoformat(cached_entry['timestamp'])
            
            # Check if expired
            age_days = (datetime.datetime.now() - timestamp).days
            if age_days > self.cache_expiry_days:
                return None
            
            return cached_entry['data']
            
        except Exception as e:
            print(f"Error reading cache: {e}")
            return None
    
    def _save_to_cache(self, city_name, data):
        """Save fetched data to cache"""
        try:
            cache = {}
            if os.path.exists(self.cache_path):
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
            
            cache[city_name] = {
                'data': data,
                'timestamp': datetime.datetime.now().isoformat()
            }
            
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=4, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error saving to cache: {e}")
    
    def fetch_from_ins(self, city_name):
        """
        Fetch data from INS (Institutul National de Statistica) API.
        PLACEHOLDER: To be implemented when INS API becomes available.
        Returns None for now.
        """
        print(f"INS API integration not yet available for {city_name}")
        # Future implementation will call INS API here
        # Expected return format: dict with population, demographics, etc.
        return None
    
    def fetch_from_brat(self, city_name):
        """
        Fetch data from BRAT (Romanian Audience Measurement) API.
        PLACEHOLDER: To be implemented when BRAT API becomes available.
        Returns None for now.
        """
        print(f"BRAT API integration not yet available for {city_name}")
        # Future implementation will call BRAT API here
        # Expected return format: dict with traffic, audience data, etc.
        return None

