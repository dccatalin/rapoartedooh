from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, Spacer, Image, Table, TableStyle, PageBreak, SimpleDocTemplate
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
import datetime
import os
import random
from src.reporting.report_generator import ReportGenerator
from src.data.city_data_manager import CityDataManager
from src.data.company_settings import CompanySettings
from src.utils.map_service import MapService
from src.utils.i18n import _, remove_diacritics

class ReportTemplates:
    """Templates for report text variations"""
    
    INTRO = [
        _("Prezentul raport detaliaza performanta estimata a campaniei Mobile DOOH pentru clientul <b>{client_name}</b>."),
        _("Acest document prezinta o analiza a impactului campaniei Mobile DOOH desfasurate pentru <b>{client_name}</b>."),
        _("Urmatorul raport ofera o imagine de ansamblu asupra rezultatelor estimate pentru campania Mobile DOOH a clientului <b>{client_name}</b>.")
    ]
    
    DEMOGRAPHICS = [
        _("{city_display} are o populatie urbana estimata la <b>{population:,} locuitori</b>. Populatia activa este de aproximativ <b>{pop_active:,}</b> ({active_pct}%)."),
        _("In {city_display}, populatia urbana este de cca. <b>{population:,} locuitori</b>, cu un segment activ de <b>{pop_active:,}</b> ({active_pct}%)."),
        _("Analiza demografica pentru {city_display} indica o populatie de <b>{population:,}</b>, din care <b>{pop_active:,}</b> ({active_pct}%) reprezinta populatia activa.")
    ]
    
    CONCLUSIONS = [
        _("Campania a generat un numar estimat de <b>{impressions:,} impresii</b>, atingand un public larg in {city_display}. Stationarea de {stationing} minute pe ora a maximizat vizibilitatea in zonele pietonale cheie."),
        _("Cu un total estimat de <b>{impressions:,} impresii</b>, campania a avut un impact semnificativ in {city_display}. Timpul de stationare ({stationing} min/ora) a contribuit la cresterea vizibilitatii."),
        _("Rezultatele indica <b>{impressions:,} impresii</b> generate in {city_display}. Strategia de stationare ({stationing} min/ora) a asigurat o expunere optima catre publicul tinta.")
    ]

CAMPAIGN_MODES = {
    'NEARBY_TOUR': {'label': _('🌍 Nearby Cities Tour (1 Vehicul)')},
    'MULTI_VEHICLE_SAME': {'label': _('🚛 Multiple Vehicule - Aceeasi Conj.')},
    'MULTI_VEHICLE_CUSTOM': {'label': _('🛠️ Multiple Vehicule - Custom Config')},
    'SINGLE_VEHICLE_CITY': {'label': _('📍 Un singur Vehicul, Un singur Oras')}
}

class CampaignReportGenerator(ReportGenerator):
    def __init__(self, data_manager):
        super().__init__(data_manager)
        self.city_manager = CityDataManager()
        self.company_settings = CompanySettings()

    def _get_styles(self):
        """Get report styles"""
        return self.styles

    def generate_campaign_report(self, campaign_data, output_path=None, output_dir=None):
        """
        Generate a comprehensive Mobile DOOH Campaign Report.
        """
        # Ensure dates are datetime.date objects
        if isinstance(campaign_data.get('start_date'), str):
            campaign_data['start_date'] = datetime.date.fromisoformat(campaign_data['start_date'])
        if isinstance(campaign_data.get('end_date'), str):
            campaign_data['end_date'] = datetime.date.fromisoformat(campaign_data['end_date'])

        # Auto-fill city data if available and missing
        # Handle multi-city aggregation
        cities = campaign_data.get('cities', [])
        if not cities and 'city' in campaign_data:
            cities = [campaign_data['city']]
            
        # Per-city configuration
        city_periods = campaign_data.get('city_periods', {})
        city_schedules = campaign_data.get('city_schedules', {})
            
        if cities:
            total_population = 0
            total_traffic = 0
            total_pedestrian = 0
            weighted_active_pop = 0
            
            # Aggregate data from all cities
            for city in cities:
                # Determine city-specific start date for data retrieval
                c_period = city_periods.get(city, {})
                
                # Handle list of periods (take first one for profile lookup)
                if isinstance(c_period, list):
                    if len(c_period) > 0:
                        c_period = c_period[0]
                    else:
                        c_period = {}
                
                # Safety check
                if not isinstance(c_period, dict):
                    c_period = {}
                    
                c_start = c_period.get('start', campaign_data['start_date'])
                if isinstance(c_start, str):
                    c_start = datetime.date.fromisoformat(c_start)
                
                city_profile = self.city_manager.get_city_data_for_period(
                    city, 
                    c_start
                )
                
                if city_profile:
                    pop = city_profile.get('population', 100000)
                    total_population += pop
                    total_traffic += city_profile.get('daily_traffic_total', 50000)
                    total_pedestrian += city_profile.get('daily_pedestrian_total', 50000)
                    weighted_active_pop += pop * city_profile.get('active_population_pct', 60)
                else:
                    # Fallback defaults per city
                    total_population += 100000
                    total_traffic += 50000
                    total_pedestrian += 50000
                    weighted_active_pop += 100000 * 60
            
            # Update campaign data with aggregated values
            campaign_data['population'] = total_population
            campaign_data['daily_traffic_total'] = total_traffic
            campaign_data['daily_pedestrian_total'] = total_pedestrian
            campaign_data['active_population_pct'] = int(weighted_active_pop / total_population) if total_population > 0 else 60
            
            # Store aggregated cities list for display (unique and sanitized)
            unique_cities_list = sorted(list(set(cities)))
            campaign_data['display_cities'] = remove_diacritics(", ".join(unique_cities_list))
        
        # Ensure defaults if still missing (fallback)
        defaults = {
            'population': 100000,
            'active_population_pct': 60,
            'daily_traffic_total': 50000,
            'daily_pedestrian_total': 50000
        }
        for k, v in defaults.items():
            if k not in campaign_data or campaign_data[k] is None:
                campaign_data[k] = v

        if output_path is None:
            client_clean = remove_diacritics(campaign_data['client_name']).replace(' ', '_')
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"campaign_report_{client_clean}_{timestamp}.pdf"
            
            if output_dir and os.path.exists(output_dir):
                output_path = os.path.join(output_dir, filename)
            else:
                output_path = self._get_report_path(filename)
            
        self._generate_campaign_pdf(campaign_data, output_path)
        self._open_report(output_path)
        return output_path

    
    def _calculate_campaign_duration(self, start_date, end_date, daily_hours_str, custom_schedule=None):
        """Calculate campaign duration metrics with peak hours consideration and custom schedules"""
        total_days = (end_date - start_date).days + 1
        
        # If custom schedule provided, calculate from that
        if custom_schedule:
            total_campaign_hours = 0
            total_peak_hours = 0
            
            for date, hours_str in custom_schedule.items():
                day_metrics = self._parse_daily_hours(hours_str)
                total_campaign_hours += day_metrics['hours']
                total_peak_hours += day_metrics['peak_hours']
            
            hours_per_day = total_campaign_hours / total_days if total_days > 0 else 0
            peak_hours_per_day = total_peak_hours / total_days if total_days > 0 else 0
            peak_hours_percentage = (total_peak_hours / total_campaign_hours * 100) if total_campaign_hours > 0 else 0
            
            return {
                'total_days': total_days,
                'hours_per_day': hours_per_day,
                'total_campaign_hours': total_campaign_hours,
                'peak_hours_per_day': peak_hours_per_day,
                'total_peak_hours': total_peak_hours,
                'peak_hours_percentage': peak_hours_percentage,
                'has_custom_schedule': True
            }
        
        # Standard calculation with uniform daily hours
        day_metrics = self._parse_daily_hours(daily_hours_str)
        hours_per_day = day_metrics['hours']
        peak_hours_per_day = day_metrics['peak_hours']
        
        total_campaign_hours = total_days * hours_per_day
        total_peak_hours = total_days * peak_hours_per_day
        peak_hours_percentage = (peak_hours_per_day / hours_per_day * 100) if hours_per_day > 0 else 0
        
        return {
            'total_days': total_days,
            'hours_per_day': hours_per_day,
            'total_campaign_hours': total_campaign_hours,
            'peak_hours_per_day': peak_hours_per_day,
            'total_peak_hours': total_peak_hours,
            'peak_hours_percentage': peak_hours_percentage,
            'has_custom_schedule': False
        }
    
    def _calculate_multi_city_metrics(self, campaign_data):
        """Calculate aggregated metrics across all cities with specific schedules and multiple periods"""
        cities = campaign_data.get('cities', [])
        if not cities and 'city' in campaign_data:
            cities = [campaign_data['city']]
            
        city_periods = campaign_data.get('city_periods', {})
        if isinstance(city_periods, list):
            # If it's a list, it might be a list of periods for a single city (legacy issue?)
            # or just corruption. Resetting is safe but causes fallback.
            city_periods = {}
            
        city_schedules = campaign_data.get('city_schedules', {})
        
        mode = campaign_data.get('campaign_mode', 'MULTI_VEHICLE_CUSTOM')
        all_vids = [campaign_data.get('vehicle_id')] + [av.get('vehicle_id') for av in campaign_data.get('additional_vehicles', [])]
        num_vehicles = len([v for v in all_vids if v])
        
        meta = city_periods.get('__meta__', {})
        is_shared = meta.get('shared_mode', False) if isinstance(meta, dict) else False
        
        # We handle both shared and individual modes using a unified 'max per vehicle' logic
        # This correctly handles tours (multiple cities for 1 vehicle = max) 
        # and simultaneous (multiple vehicles = sum).
        
        total_campaign_hours = 0
        total_peak_hours = 0
        total_active_days_set = set()
        
        v_list = all_vids if not is_shared else ["SHARED_V_PLACEHOLDER"]
        
        for v_entry in v_list:
            v_day_hours = {} # date_str -> max_hours
            v_day_peak = {}  # date_str -> max_peak
            
            if is_shared:
                # In shared mode, we check all cities
                itinerary_source = {c: city_periods.get(c, []) for c in cities if c != '__meta__'}
                schedules_source = city_schedules
            else:
                # In individual mode, we check this specific vehicle's itinerary
                itinerary_source = city_periods.get(v_entry, {})
                schedules_source = city_schedules.get(v_entry, {})
                
            if not isinstance(itinerary_source, dict): continue
            
            for city_name, periods in itinerary_source.items():
                c_schedule = schedules_source.get(city_name, {})
                if isinstance(periods, dict): periods = [periods]
                if not isinstance(periods, list): continue
                
                for period in periods:
                    if isinstance(period, list) and len(period) > 0: period = period[0]
                    if not isinstance(period, dict): continue
                    
                    start = period.get('start')
                    end = period.get('end')
                    if not start or not end: continue
                    if isinstance(start, str): start = datetime.date.fromisoformat(start[:10])
                    if isinstance(end, str): end = datetime.date.fromisoformat(end[:10])
                    
                    current = start
                    while current <= end:
                        date_str = current.strftime('%Y-%m-%d')
                        total_active_days_set.add(date_str)
                        
                        day_data = c_schedule.get(date_str)
                        if day_data and day_data.get('active', True):
                            h_str = day_data.get('hours', campaign_data['daily_hours'])
                        else:
                            # Fallback to campaign daily hours if specifically active or no data
                            h_str = campaign_data['daily_hours'] if (not day_data or day_data.get('active', True)) else "00:00-00:00"
                            
                        metrics = self._parse_daily_hours(h_str)
                        
                        # Use MAX to avoid double-counting overlapping cities for the SAME vehicle
                        v_day_hours[date_str] = max(v_day_hours.get(date_str, 0), metrics['hours'])
                        v_day_peak[date_str] = max(v_day_peak.get(date_str, 0), metrics['peak_hours'])
                        
                        current += datetime.timedelta(days=1)
            
            # Add this vehicle's contribution
            v_total = sum(v_day_hours.values())
            v_peak = sum(v_day_peak.values())
            
            if is_shared:
                # In shared mode, the placeholder results represent one vehicle's activity.
                # Since all vehicles share this config, we multiply by the total vehicle count.
                total_campaign_hours += v_total * num_vehicles
                total_peak_hours += v_peak * num_vehicles
            else:
                total_campaign_hours += v_total
                total_peak_hours += v_peak

        total_active_days = len(total_active_days_set)
        
        # Averages & Metrics
        hours_per_day = total_campaign_hours / total_active_days if total_active_days > 0 else 0
        peak_hours_per_day = total_peak_hours / total_active_days if total_active_days > 0 else 0
        peak_percentage = (total_peak_hours / total_campaign_hours * 100) if total_campaign_hours > 0 else 0
        
        return {
            'total_days': total_active_days,
            'hours_per_day': hours_per_day,
            'total_campaign_hours': total_campaign_hours,
            'peak_hours_per_day': peak_hours_per_day,
            'total_peak_hours': total_peak_hours,
            'peak_hours_percentage': peak_percentage,
            'has_custom_schedule': bool(city_schedules) or bool(campaign_data.get('custom_daily_schedule')),
            'shared_mode': is_shared,
            'campaign_mode': mode,
            'num_vehicles': num_vehicles
        }


    def _parse_daily_hours(self, hours_str):
        """Parse a daily hours string and calculate total hours and peak hours. Supports multiple intervals like '09:00-11:00, 14:00-18:00'"""
        if not hours_str or not isinstance(hours_str, str):
            return {'hours': 8, 'peak_hours': 0}
            
        total_hours = 0
        total_peak = 0
        
        # Split into multiple intervals if present
        intervals = [i.strip() for i in hours_str.split(',')]
        
        for interval in intervals:
            try:
                if '-' not in interval: continue
                start_time, end_time = interval.split('-')
                start_h = int(start_time.split(':')[0])
                start_m = int(start_time.split(':')[1]) if ':' in start_time else 0
                end_h = int(end_time.split(':')[0])
                end_m = int(end_time.split(':')[1]) if ':' in end_time else 0
                
                hours = (end_h - start_h) + (end_m - start_m) / 60
                if hours < 0: hours += 24 # Handle overnight if needed
                total_hours += hours
                
                # Calculate peak hours overlap for this interval
                peak_morning = (7, 9)
                peak_evening = (17, 19)
                
                campaign_start_h = start_h + start_m / 60
                campaign_end_h = end_h + end_m / 60
                
                # Morning peak overlap
                if campaign_start_h < peak_morning[1] and campaign_end_h > peak_morning[0]:
                    overlap_start = max(campaign_start_h, peak_morning[0])
                    overlap_end = min(campaign_end_h, peak_morning[1])
                    total_peak += max(0, overlap_end - overlap_start)
                
                # Evening peak overlap
                if campaign_start_h < peak_evening[1] and campaign_end_h > peak_evening[0]:
                    overlap_start = max(campaign_start_h, peak_evening[0])
                    overlap_end = min(campaign_end_h, peak_evening[1])
                    total_peak += max(0, overlap_end - overlap_start)
            except Exception as e:
                print(f"Error parsing interval {interval}: {e}")
                continue
        
        if total_hours == 0:
            return {'hours': 8, 'peak_hours': 0} # Fallback
            
        return {
            'hours': total_hours,
            'peak_hours': total_peak
        }
    
    def _calculate_route_distance(self, speed_kmh, total_hours, stationing_min_per_hour, avg_commute_distance_km=8, known_distance_total=None, custom_daily_distances=None, total_days=1):
        """Calculate route distance and coverage metrics, using known distance if provided"""
        # If custom daily distances provided, use them
        if custom_daily_distances:
            total_km = sum(custom_daily_distances.values())
            used_known_distance = True
        # If known total distance is provided, use it
        elif known_distance_total is not None and known_distance_total > 0:
            total_km = known_distance_total
            used_known_distance = True
        else:
            # Calculate from speed and hours
            stationing_hours = (stationing_min_per_hour / 60) * total_hours
            effective_driving_hours = total_hours - stationing_hours
            total_km = speed_kmh * effective_driving_hours
            used_known_distance = False
        
        # Calculate effective driving hours from distance
        if used_known_distance:
            # Reverse calculate effective hours
            effective_driving_hours = total_km / speed_kmh if speed_kmh > 0 else 0
        else:
            stationing_hours = (stationing_min_per_hour / 60) * total_hours
            effective_driving_hours = total_hours - stationing_hours
        
        # Calculate route loops
        route_loops = total_km / avg_commute_distance_km if avg_commute_distance_km > 0 else 0
        
        return {
            'total_km': int(total_km),
            'effective_driving_hours': round(effective_driving_hours, 1),
            'route_loops': round(route_loops, 1),
            'used_known_distance': used_known_distance
        }
    
    def _calculate_impressions_by_mode(self, modal_split, daily_traffic, daily_pedestrian, campaign_hours_per_day, total_days, start_date, city_name, spot_duration=10, loop_duration=60, is_exclusive=False, city_schedule=None):
        """Calculate impressions split by transport mode, accounting for special events and spot share of voice"""
        
        # Calculate Spot Frequency Factor (Share of Voice)
        if is_exclusive:
            share_of_voice = 1.0
        else:
            share_of_voice = spot_duration / loop_duration if loop_duration > 0 else 0.16 # Default ~1/6
            
        # Calculate hourly rates (base)
        hourly_traffic_base = daily_traffic / 24
        hourly_pedestrian_base = daily_pedestrian / 24
        
        total_campaign_traffic = 0
        total_campaign_pedestrian = 0
        
        # Iterate through each day to check for special events
        current_date = start_date
        events_encountered = []
        
        for i in range(total_days):
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Determine hours for this day
            hours_today = campaign_hours_per_day
            if city_schedule:
                day_data = city_schedule.get(date_str)
                if day_data:
                    if not day_data.get('active', True):
                        hours_today = 0
                    else:
                        h_str = day_data.get('hours')
                        if h_str:
                            metrics = self._parse_daily_hours(h_str)
                            hours_today = metrics['hours']
            
            if hours_today > 0:
                # Get multipliers for this day
                t_mult, p_mult, event_name = self.city_manager.get_event_multipliers(city_name, current_date)
                
                if event_name and event_name not in events_encountered:
                    events_encountered.append(event_name)
                
                # Daily traffic for this specific day
                daily_t = hourly_traffic_base * hours_today * t_mult
                daily_p = hourly_pedestrian_base * hours_today * p_mult
                
                total_campaign_traffic += daily_t
                total_campaign_pedestrian += daily_p
            
            current_date += datetime.timedelta(days=1)
        
        # Split by mode using modal split percentages
        auto_traffic = total_campaign_traffic * (modal_split.get('auto', 35) / 100)
        cycling_traffic = total_campaign_traffic * (modal_split.get('cycling', 4) / 100)
        walking_traffic = total_campaign_pedestrian * (modal_split.get('walking', 27) / 100)
        
        # Calculate impressions with visibility, occupancy, and Share of Voice
        # For exclusive campaigns, visibility is 100% (1.0) as requested
        visibility_factor = 1.0 if is_exclusive else 0.7  # 70% standard visibility rate
        
        auto_occupancy = 1.65  # Average occupants per vehicle
        
        # Apply Share of Voice to final impressions
        auto_impressions = auto_traffic * auto_occupancy * visibility_factor * share_of_voice
        pedestrian_impressions = (walking_traffic + cycling_traffic) * visibility_factor * share_of_voice
        
        return {
            'auto': int(auto_impressions),
            'pedestrian': int(pedestrian_impressions),
            'total': int(auto_impressions + pedestrian_impressions),
            'events': events_encountered,
            'share_of_voice': share_of_voice
        }
    
    def _calculate_ots_and_reach(self, total_impressions, route_loops, active_population):
        """Calculate OTS and Reach based on route coverage"""
        # Coverage factor: more loops = higher coverage, max 100% at 10+ loops
        coverage_factor = min(route_loops / 10, 1.0)
        
        # Unique viewers: percentage of active population based on coverage
        unique_rate = 0.6 * coverage_factor  # 60% max unique rate
        reach = int(active_population * unique_rate)
        
        # OTS = total impressions / unique viewers
        ots = round(total_impressions / reach, 1) if reach > 0 else 1.0
        
        return {
            'reach': reach,
            'ots': ots
        }


    def _generate_campaign_pdf(self, data, output_path):
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle, Image, Paragraph, Spacer
        
        # Consolidate core variables to avoid UnboundLocalError
        cities = data.get('cities', [])
        if not cities and 'city' in data:
            cities = [data['city']]
        
        meta = data.get('city_periods', {}).get('__meta__', {})
        shared_mode = meta.get('shared_mode', True)
        
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        
        # Helper to clean data strings
        client_name = remove_diacritics(data['client_name'])
        campaign_name = remove_diacritics(data['campaign_name'])
        
        # --- Company Header ---
        settings = self.company_settings.get_settings()
        if settings:
            # Logo
            logo_path = settings.get('logo_path')
            if logo_path and os.path.exists(logo_path):
                try:
                    # Place logo at top left
                    logo = Image(logo_path, width=1.5*inch, height=0.8*inch)
                    logo.hAlign = 'LEFT'
                    story.append(logo)
                    story.append(Spacer(1, 6))
                except Exception as e:
                    print(f"Error loading logo: {e}")
            
            # Company Details
            comp_name = settings.get('name', '')
            comp_addr = settings.get('address', '')
            comp_reg = settings.get('registration_number', '')
            
            if comp_name:
                header_style = ParagraphStyle(
                    'CompanyHeader',
                    parent=self.styles['Normal'],
                    fontSize=8,
                    textColor=colors.grey,
                    alignment=0 # Left
                )
                header_text = f"<b>{comp_name}</b>"
                if comp_reg: header_text += f" | {comp_reg}"
                if comp_addr: header_text += f"<br/>{comp_addr}"
                story.append(Paragraph(header_text, header_style))
                story.append(Spacer(1, 12))
        
        # Select templates
        intro_tmpl = random.choice(ReportTemplates.INTRO)
        story.append(Paragraph(remove_diacritics(intro_tmpl.format(client_name=client_name)), self.styles['Normal']))
        story.append(Spacer(1, 12))
        
        if 'display_cities' in data:
            city_display = remove_diacritics(data['display_cities'])
        else:
            city_display = remove_diacritics(data.get('city', 'Unknown'))
            
        start_date = data['start_date'].strftime('%d.%m.%Y')
        end_date = data['end_date'].strftime('%d.%m.%Y')
        
        # Title
        story.append(Paragraph(f"<b>" + remove_diacritics(_("Campaign Report") + f": {campaign_name}</b>"), self.styles['Title']))
        story.append(Spacer(1, 12))
        
        # Campaign Details Table
        normal_style = self.styles['Normal']
        data_table = [
            [remove_diacritics(_("Client") + ":"), Paragraph(client_name, normal_style)],
            [remove_diacritics(_("Campaign") + ":"), Paragraph(campaign_name, normal_style)],
            [remove_diacritics(_("PO Number (Optional)") + ":"), Paragraph(str(data.get('po_number', '-')), normal_style)],
            [remove_diacritics(_("City") + "(e):"), Paragraph(city_display, normal_style)],
            [remove_diacritics(_("Period") + ":"), Paragraph(f"{start_date} - {end_date}", normal_style)],
            [remove_diacritics(_("Daily Hours") + ":"), Paragraph(str(data['daily_hours']), normal_style)]
        ]
        
        # Add Route Info if available
        if data.get('route_data'):
            route = data['route_data']
            data_table.append([remove_diacritics(_("Route") + ":"), Paragraph(remove_diacritics(route.get('name', 'Custom Route')), normal_style)])
            data_table.append([remove_diacritics(_("Distance") + " " + _("Route") + ":"), Paragraph(f"{route.get('distance_km', 0)} km", normal_style)])
        elif data.get('known_distance_total'):
             data_table.append([remove_diacritics(_("Total Distance") + ":"), Paragraph(f"{data['known_distance_total']} km", normal_style)])
             
        # Add POIs if available
        if data.get('pois'):
            pois = remove_diacritics(data['pois']).replace('\n', ', ')
            data_table.append([remove_diacritics(_("Points of Interest") + ":"), Paragraph(pois, normal_style)])
            
        # Create and style the table
        t = Table(data_table, colWidths=[1.5*inch, 5*inch])
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 24))
        
        # --- Map Section ---
        google_key = settings.get('google_maps_api_key')
        mapbox_key = settings.get('mapbox_api_key')
        
        if (google_key or mapbox_key) and 'cities' in data and data['cities']:
            try:
                map_service = MapService(google_key, mapbox_key)
                map_path = os.path.join(os.path.dirname(output_path), "temp_map.png")
                route_cities = data.get('route_data', {}).get('route', data['cities'])
                coordinates = []
                from src.utils.route_optimizer import RouteOptimizer
                optimizer = RouteOptimizer()
                for city in route_cities:
                    coords = optimizer.CITY_COORDINATES.get(city)
                    if coords:
                        coordinates.append(coords)
                
                if map_service.download_map_image(route_cities, map_path, coordinates):
                    story.append(Paragraph(remove_diacritics(_("Route Map (Automatically Generated)")), self.styles['Heading3']))
                    story.append(Image(map_path, width=6*inch, height=4*inch))
                    story.append(Spacer(1, 24))
            except Exception as e:
                print(f"Error generating map: {e}")
        
        # Calculate campaign duration metrics
        if 'city_periods' in data or 'city_schedules' in data:
            duration_metrics = self._calculate_multi_city_metrics(data)
        else:
            duration_metrics = self._calculate_campaign_duration(
                data['start_date'], 
                data['end_date'], 
                data['daily_hours'],
                data.get('custom_daily_schedule')
            )
        
        # Basic Info
        info_style = self.styles['Normal']
        story.append(Paragraph(f"<b>{remove_diacritics(_('Report Date'))}:</b> {datetime.date.today().strftime('%d %B %Y')}", info_style))
        story.append(Paragraph(f"<b>{remove_diacritics(_('Campaign Period'))}:</b> {data['start_date'].strftime('%d')} - {data['end_date'].strftime('%d %B %Y')} ({remove_diacritics(_('Total active days'))}: {duration_metrics['total_days']})", info_style))
        story.append(Paragraph(f"<b>{remove_diacritics(_('Daily Hours'))}:</b> {data['daily_hours']} ({remove_diacritics(_('Average'))}: {duration_metrics['hours_per_day']:.1f} {remove_diacritics(_('hours/day'))}{' - ' + remove_diacritics(_('Different schedule')) if duration_metrics.get('has_custom_schedule') else ''})", info_style))
        story.append(Paragraph(f"<b>{remove_diacritics(_('Total Exposure Duration'))}:</b> {duration_metrics['total_campaign_hours']:.1f} {remove_diacritics(_('hours'))}", info_style))
        
        if duration_metrics.get('peak_hours_per_day', 0) > 0:
            story.append(Paragraph(f"<b>" + _("Peak hours covered") + f":</b> {duration_metrics['peak_hours_per_day']:.1f} " + _("hours/day") + f" ({duration_metrics['peak_hours_percentage']:.0f}% " + _("of schedule") + f") - Total: {duration_metrics['total_peak_hours']:.1f} " + _("hours"), info_style))
        
        # Vehicle Info
        if data.get('vehicle_name'):
             v_info = f"<b>{remove_diacritics(_('Vehicle'))}:</b> {data['vehicle_name']} ({data.get('vehicle_registration', '')})"
             if data.get('driver_name'):
                  v_info += f" | <b>{remove_diacritics(_('Driver'))}:</b> {remove_diacritics(data['driver_name'])}"
             story.append(Paragraph(v_info, info_style))
             
        if duration_metrics.get('campaign_mode'):
            campaign_mode_key = duration_metrics['campaign_mode']
            mode_data = CAMPAIGN_MODES.get(campaign_mode_key, {})
            if mode_data:
                story.append(Paragraph(f"<b>{remove_diacritics(_('Deployment Mode'))}:</b> {mode_data.get('label')}", normal_style))

        story.append(Paragraph(f"<b>{remove_diacritics(_('Objective'))}:</b> {remove_diacritics(_('Estimation of pedestrian and auto traffic exposed, correlated with demographic data and urban mobility.'))}", info_style))
        story.append(Spacer(1, 15))
        
        # --- Multi-Report Breakdown Section ---
        if len(cities) > 1 or duration_metrics.get('num_vehicles', 1) > 1:
            story.append(Paragraph(remove_diacritics(_("Detailed Deployment Breakdown")), self.styles['Heading2']))
            breakdown_data = [[remove_diacritics(x) for x in [_("City"), _("Period"), _("Days"), _("Daily Hours"), _("Total Hours")]]]
            
            for city in cities:
                # Fetch specific periods for this city to show real start/end
                c_periods = []
                c_hours_str = data['daily_hours']
                
                # Try to find city periods in data
                # We need to look in both root (shared) and vehicle keys (individual)
                # But 'cities' list usually implies we are iterating known cities.
                # In SHARED mode, city_periods[city] exists.
                # In INDIVIDUAL mode, we have to find which vehicle covers this city or aggregate.
                
                cp_source = data.get('city_periods', {})
                cs_source = data.get('city_schedules', {})
                
                # Check root (shared)
                if city in cp_source and isinstance(cp_source[city], list):
                    c_periods = cp_source[city]
                    # Check schedule in root
                    if city in cs_source and isinstance(cs_source[city], dict):
                         # Extract hours from first active day
                         for d_val in cs_source[city].values():
                             if d_val.get('active', True) and d_val.get('hours'):
                                 c_hours_str = d_val['hours']
                                 break
                else:
                    # Check vehicles (individual) - take first vehicle that has this city
                    # This is a simplification for the report if multiple vehicles go to same city with diff schedules
                    for k, v in cp_source.items():
                        if k == '__meta__': continue
                        if isinstance(v, dict) and city in v:
                            c_periods = v[city]
                            # Check vehicle schedule
                            v_sched = cs_source.get(k, {}).get(city, {})
                            for d_val in v_sched.values():
                                 if d_val.get('active', True) and d_val.get('hours'):
                                     c_hours_str = d_val['hours']
                                     break
                            break
                            
                # Calculate specific dates
                if c_periods:
                    c_starts = [p['start'] for p in c_periods if 'start' in p]
                    c_ends = [p['end'] for p in c_periods if 'end' in p]
                    s_date = min(c_starts) if c_starts else data['start_date'].strftime('%Y-%m-%d')
                    e_date = max(c_ends) if c_ends else data['end_date'].strftime('%Y-%m-%d')
                    
                    # Convert to display format
                    try:
                        s_dt = datetime.date.fromisoformat(s_date[:10])
                        e_dt = datetime.date.fromisoformat(e_date[:10])
                        period_str = f"{s_dt.strftime('%d.%m')} - {e_dt.strftime('%d.%m')}"
                        days_count = (e_dt - s_dt).days + 1
                    except:
                        period_str = f"{data['start_date'].strftime('%d.%m')} - {data['end_date'].strftime('%d.%m')}"
                        days_count = duration_metrics['total_days']
                else:
                    period_str = f"{data['start_date'].strftime('%d.%m')} - {data['end_date'].strftime('%d.%m')}"
                    days_count = duration_metrics['total_days']

                breakdown_data.append([
                    remove_diacritics(city),
                    period_str,
                    f"{days_count}",
                    c_hours_str,
                    f"{duration_metrics['total_campaign_hours'] / len(cities):.1f}" if duration_metrics.get('campaign_mode') == 'NEARBY_TOUR' else _("Simultaneous")
                ])
            
            table = Table(breakdown_data, colWidths=[120, 100, 50, 100, 80])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            story.append(table)
            story.append(Spacer(1, 24))

        # --- 1. Demographic Context ---
        story.append(Paragraph("1. " + remove_diacritics(_("Demographic Context and Urban Mobility")), self.styles['Heading2']))
        pop_active = int(data['population'] * data['active_population_pct'] / 100)
        demo_tmpl = random.choice(ReportTemplates.DEMOGRAPHICS)
        story.append(Paragraph(remove_diacritics(demo_tmpl.format(
            city_display=city_display,
            population=data['population'],
            pop_active=pop_active,
            active_pct=data['active_population_pct']
        )), info_style))
        story.append(Spacer(1, 12))
        
        default_modal_split = {'auto': 35, 'walking': 27, 'cycling': 4, 'public_transport': 34}
        total_population = 0
        weighted_modal_split = {'auto': 0, 'walking': 0, 'cycling': 0, 'public_transport': 0}
        avg_commute_distance = 0
        
        for city in cities:
            city_profile = self.city_manager.get_city_data_for_period(city, data['start_date'])
            pop = city_profile.get('population', 100000) if city_profile else 100000
            total_population += pop
            city_modal_split = city_profile.get('modal_split', default_modal_split) if city_profile else default_modal_split
            for mode in weighted_modal_split:
                weighted_modal_split[mode] += city_modal_split.get(mode, default_modal_split[mode]) * pop
            avg_commute_distance += (city_profile.get('avg_commute_distance_km', 8) if city_profile else 8) * pop
        
        if total_population > 0:
            modal_split = {mode: int(value / total_population) for mode, value in weighted_modal_split.items()}
            avg_commute_distance = avg_commute_distance / total_population
        else:
            modal_split = default_modal_split
            avg_commute_distance = 8
        
        split_data = {
            remove_diacritics(_('Personal Auto')): modal_split['auto'],
            remove_diacritics(_('Public Transport')): modal_split['public_transport'],
            remove_diacritics(_('Pedestrian')): modal_split['walking'],
            remove_diacritics(_('Bicycle')): modal_split['cycling']
        }
        chart_buf = self.create_pie_chart(split_data, remove_diacritics(_("Transport Modes Distribution (Estimated)")))
        if chart_buf:
            story.append(Image(chart_buf, width=4*inch, height=4*inch))
        story.append(Spacer(1, 12))

        # --- 2. Traffic Estimates ---
        story.append(Paragraph("2. " + remove_diacritics(_("Traffic Estimates (Campaign Interval)")), self.styles['Heading2']))
        
        # Calculate impressions
        total_impressions_data = {'auto': 0, 'pedestrian': 0, 'total': 0, 'events': []}
        all_vids = [data.get('vehicle_id')] + [av.get('vehicle_id') for av in data.get('additional_vehicles', [])]
        num_vehicles = len([v for v in all_vids if v]) or 1

        if not shared_mode:
            for v_id in all_vids:
                if not v_id: continue
                v_itinerary = data.get('city_periods', {}).get(v_id, {})
                v_schedules_map = data.get('city_schedules', {}).get(v_id, {})
                if not isinstance(v_itinerary, dict): continue
                for city_name, periods in v_itinerary.items():
                    c_schedule = v_schedules_map.get(city_name, {}) if isinstance(v_schedules_map, dict) else {}
                    period = periods[0] if isinstance(periods, list) and periods else (periods if isinstance(periods, dict) else {})
                    if not period: continue
                    c_start = datetime.date.fromisoformat(period['start']) if isinstance(period.get('start'), str) else period.get('start')
                    c_end = datetime.date.fromisoformat(period['end']) if isinstance(period.get('end'), str) else period.get('end')
                    if not c_start or not c_end: continue
                    c_days = (c_end - c_start).days + 1
                    city_profile = self.city_manager.get_city_data_for_period(city_name, c_start)
                    if not city_profile: continue
                    inc = self._calculate_impressions_by_mode(
                        city_profile.get('modal_split', default_modal_split),
                        city_profile.get('daily_traffic_total', 50000),
                        city_profile.get('daily_pedestrian_total', 50000),
                        duration_metrics['hours_per_day'], c_days, c_start, city_name,
                        spot_duration=data.get('spot_duration_sec', 10),
                        loop_duration=data.get('loop_duration_sec', 60),
                        is_exclusive=data.get('is_exclusive', False),
                        city_schedule=c_schedule
                    )
                    total_impressions_data['auto'] += inc['auto']
                    total_impressions_data['pedestrian'] += inc['pedestrian']
                    total_impressions_data['total'] += inc['total']
                    for ev in inc['events']:
                        if ev not in total_impressions_data['events']: total_impressions_data['events'].append(ev)
            impressions = total_impressions_data
        else:
            for city_name in cities:
                all_periods = data.get('city_periods', {})
                periods = all_periods.get(city_name, [{'start': data['start_date'], 'end': data['end_date']}])
                if isinstance(periods, dict): periods = [periods]
                all_schedules = data.get('city_schedules', {})
                c_schedule = all_schedules.get(city_name)
                for period in periods:
                    c_start = datetime.date.fromisoformat(period['start']) if isinstance(period.get('start'), str) else period.get('start')
                    c_end = datetime.date.fromisoformat(period['end']) if isinstance(period.get('end'), str) else period.get('end')
                    if not c_start or not c_end: continue
                    c_days = (c_end - c_start).days + 1
                    city_profile = self.city_manager.get_city_data_for_period(city_name, c_start)
                    if not city_profile: continue
                    inc = self._calculate_impressions_by_mode(
                        city_profile.get('modal_split', default_modal_split),
                        city_profile.get('daily_traffic_total', 50000),
                        city_profile.get('daily_pedestrian_total', 50000),
                        duration_metrics['hours_per_day'], c_days, c_start, city_name,
                        spot_duration=data.get('spot_duration_sec', 10),
                        loop_duration=data.get('loop_duration_sec', 60),
                        is_exclusive=data.get('is_exclusive', False),
                        city_schedule=c_schedule
                    )
                    total_impressions_data['auto'] += inc['auto'] * num_vehicles
                    total_impressions_data['pedestrian'] += inc['pedestrian'] * num_vehicles
                    total_impressions_data['total'] += inc['total'] * num_vehicles
                    for ev in inc['events']:
                        if ev not in total_impressions_data['events']: total_impressions_data['events'].append(ev)
            impressions = total_impressions_data

        # --- OTS and reach ---
        route_metrics = self._calculate_route_distance(
            data['vehicle_speed_kmh'], duration_metrics['total_campaign_hours'],
            data['stationing_min_per_hour'], avg_commute_distance,
            data.get('known_distance_total'), data.get('custom_daily_distances'), duration_metrics['total_days']
        )
        audience_metrics = self._calculate_ots_and_reach(impressions['total'], route_metrics['route_loops'], pop_active)
        reach, ots = audience_metrics['reach'], audience_metrics['ots']

        # --- Tables and summary ---
        story.append(Paragraph(remove_diacritics(_("Global Metrics")), self.styles['Heading2']))
        metrics_data = [
            [remove_diacritics(x) for x in [_("Metric"), _("Value"), _("Description")]],
            [remove_diacritics(_("Total Impressions")), f"{impressions['total']:,}", remove_diacritics(_("Estimated visual contacts"))],
            [remove_diacritics(_("Total Hours")), f"{duration_metrics['total_campaign_hours']:.1f}", remove_diacritics(_("Net broadcasting time"))],
            [remove_diacritics(_("Avg Speed")), f"{data['vehicle_speed_kmh']} km/h", remove_diacritics(_("Average traffic speed"))],
            [remove_diacritics(_("Stationing")), f"{data['stationing_min_per_hour']} min/h", remove_diacritics(_("Broadcasting while parked"))],
            [remove_diacritics(_("Reach Potential")), f"{reach:,}", remove_diacritics(_("Unique viewers"))],
            [remove_diacritics(_("OTS")), f"{ots}", remove_diacritics(_("Opportunity to See"))]
        ]
        t_metrics = Table(metrics_data, colWidths=[1.5*inch, 1.5*inch, 3.5*inch])
        t_metrics.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t_metrics)
        story.append(Spacer(1, 24))

        # Impressions Chart
        imp_data = {remove_diacritics(_('Auto')): impressions['auto'], remove_diacritics(_('Pedestrian/Bicycle')): impressions['pedestrian']}
        imp_chart = self.create_pie_chart(imp_data, remove_diacritics(_("Impressions Distribution")))
        if imp_chart:
            story.append(Image(imp_chart, width=4*inch, height=4*inch))
        story.append(Spacer(1, 24))

        # --- Conclusions ---
        story.append(Paragraph("4. " + remove_diacritics(_("Conclusions")), self.styles['Heading2']))
        concl_tmpl = random.choice(ReportTemplates.CONCLUSIONS)
        story.append(Paragraph(remove_diacritics(concl_tmpl.format(
            impressions=impressions['total'],
            city_display=city_display,
            stationing=data['stationing_min_per_hour']
        )), info_style))
        story.append(Spacer(1, 12))
        story.append(Paragraph("<i>" + remove_diacritics(_("*This report is based on statistical estimates and average traffic data.")) + "</i>", self.styles['Italic']))

        doc.build(story)
