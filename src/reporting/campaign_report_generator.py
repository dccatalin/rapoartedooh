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
from src.data.report_storage import ReportStorage
from src.data.vehicle_manager import VehicleManager
from src.data.driver_manager import DriverManager

class ReportTemplates:
    """Templates for report text variations"""
    
    INTRO = [
        _("Prezentul raport detaliaza performanta estimata a campaniei Mobile DOOH pentru clientul <b>{client_name}</b>, bazat pe indicatori de audienta stradala (impressions), reach potential si frecventa (OTS)."),
        _("Analiza de impact pentru campania Mobile DOOH a clientului <b>{client_name}</b>. Datele reflecta expunerea auditata in functie de dinamica fluxurilor de trafic si mobilitate urbana."),
        _("Acest document ofera o estimare conservativa a rezultatelor campaniei Mobile DOOH ({client_name}), coreland datele demografice locale cu parametrii tehnici ai vehiculului de broadcasting.")
    ]
    
    DEMOGRAPHICS = [
        _("{city_display} are o populatie urbana estimata la <b>{population:,} locuitori</b>. Segmentul activ (lucratori si studenti, 18-65 ani) reprezinta cca. <b>{pop_active:,}</b> ({active_pct}%)."),
        _("Analiza pentru {city_display} indica un bazin demografic de <b>{population:,} locuitori</b>. Mobilitatea zilnica medie este de 2.5-3 deplasari/persoana, concentrata pe axele comerciale si centrale."),
        _("In {city_display}, densitatea urbana si fluxurile radiale (centru-periferie) definesc o populatie activa de <b>{pop_active:,}</b> ({active_pct}%), cu un mix de transport personal (65-77%) si pietonal.")
    ]
    
    CONCLUSIONS = [
        _("Campania a generat <b>{impressions:,} impresii</b>. Strategia de stationare ({stationing} min/ora) in hotspot-uri congestionate a optimizat timpul de expunere, rezultand intr-o frecventa (OTS) ridicata."),
        _("Rezultatul de <b>{impressions:,} impresii</b> confirma eficienta rutei alese. Viteza medie redusa si punctele de stationare au asigurat o vizibilitate maxima catre segmentul de public tinta in {city_display}."),
        _("Cu un reach estimat semnificativ, campania a atins obiectivele de vizibilitate. Cele <b>{impressions:,} impresii</b> reflecta o penetrare optima a pietei locale, sustinuta de mobilitatea radiala intensa.")
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
        self.report_storage = ReportStorage()
        self.vehicle_manager = VehicleManager()
        self.driver_manager = DriverManager()

    def _get_styles(self):
        """Get report styles"""
        return self.styles

    def generate_campaign_report(self, campaign_data, output_path=None, output_dir=None):
        """Generate a comprehensive Mobile DOOH Campaign Report."""
        self._prepare_data_internal(campaign_data)

        if output_path is None:
            client_clean = remove_diacritics(campaign_data['client_name']).replace(' ', '_')
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"campaign_report_{client_clean}_{timestamp}.pdf"
            output_path = os.path.join(output_dir, filename) if output_dir and os.path.exists(output_dir) else self._get_report_path(filename)
            
        # Collect calculated metadata for persistence
        metrics = self._generate_campaign_pdf(campaign_data, output_path)
        self._open_report(output_path)
        
        # Save to database
        try:
            self.report_storage.save_report_metadata(
                campaign_id=campaign_data['id'],
                report_type='standard',
                file_path=output_path,
                file_name=os.path.basename(output_path),
                frozen_data=metrics
            )
        except Exception as e:
            # Don't fail the whole generation if storage fails, but log it
            import logging
            logging.getLogger(__name__).error(f"Failed to save report history: {e}")

        return output_path

    def _prepare_data_internal(self, campaign_data):
        """Unified data preparation for all reports"""
        if isinstance(campaign_data.get('start_date'), str):
            campaign_data['start_date'] = datetime.date.fromisoformat(campaign_data['start_date'][:10])
        if isinstance(campaign_data.get('end_date'), str):
            campaign_data['end_date'] = datetime.date.fromisoformat(campaign_data['end_date'][:10])

        cities = campaign_data.get('cities', [])
        if not cities and 'city' in campaign_data:
            cities = [campaign_data['city']]
            
        city_periods = campaign_data.get('city_periods', {})
        if cities:
            total_population, total_traffic, total_pedestrian, weighted_active_pop = 0, 0, 0, 0
            for city in cities:
                c_period = city_periods.get(city, {})
                if isinstance(c_period, list): c_period = c_period[0] if c_period else {}
                c_start = c_period.get('start', campaign_data['start_date'])
                if isinstance(c_start, str): c_start = datetime.date.fromisoformat(c_start[:10])
                city_profile = self.city_manager.get_city_data_for_period(city, c_start)
                if city_profile:
                    pop = city_profile.get('population', 100000)
                    total_population += pop; total_traffic += city_profile.get('daily_traffic_total', 50000); total_pedestrian += city_profile.get('daily_pedestrian_total', 50000)
                    weighted_active_pop += pop * city_profile.get('active_population_pct', 60)
                else:
                    total_population += 100000; total_traffic += 50000; total_pedestrian += 50000; weighted_active_pop += 100000 * 60
            campaign_data['population'] = total_population
            campaign_data['daily_traffic_total'] = total_traffic
            campaign_data['daily_pedestrian_total'] = total_pedestrian
            campaign_data['active_population_pct'] = int(weighted_active_pop / total_population) if total_population > 0 else 60
            campaign_data['display_cities'] = remove_diacritics(", ".join(sorted(list(set(cities)))))
        
        defaults = {'population': 100000, 'active_population_pct': 60, 'daily_traffic_total': 50000, 'daily_pedestrian_total': 50000}
        for k, v in defaults.items():
            if k not in campaign_data or campaign_data[k] is None: campaign_data[k] = v

    def _calculate_campaign_duration(self, start_date, end_date, daily_hours_str, custom_schedule=None):
        total_days = (end_date - start_date).days + 1
        if custom_schedule:
            total_campaign_hours = 0
            total_peak_hours = 0
            for date, hours_str in custom_schedule.items():
                day_metrics = self._parse_daily_hours(hours_str)
                total_campaign_hours += day_metrics['hours']
                total_peak_hours += day_metrics['peak_hours']
            return {
                'total_days': total_days, 'hours_per_day': total_campaign_hours / total_days if total_days > 0 else 0,
                'total_campaign_hours': total_campaign_hours, 'peak_hours_per_day': total_peak_hours / total_days if total_days > 0 else 0,
                'total_peak_hours': total_peak_hours, 'peak_hours_percentage': (total_peak_hours / total_campaign_hours * 100) if total_campaign_hours > 0 else 0,
                'has_custom_schedule': True
            }
        day_metrics = self._parse_daily_hours(daily_hours_str)
        hours_per_day = day_metrics['hours']
        peak_hours_per_day = day_metrics['peak_hours']
        return {
            'total_days': total_days, 'hours_per_day': hours_per_day, 'total_campaign_hours': total_days * hours_per_day,
            'peak_hours_per_day': peak_hours_per_day, 'total_peak_hours': total_days * peak_hours_per_day,
            'peak_hours_percentage': (peak_hours_per_day / hours_per_day * 100) if hours_per_day > 0 else 0,
            'has_custom_schedule': False
        }

    def _calculate_multi_city_metrics(self, campaign_data):
        cities = campaign_data.get('cities', [])
        if not cities and 'city' in campaign_data: cities = [campaign_data['city']]
        city_periods = campaign_data.get('city_periods', {})
        city_schedules = campaign_data.get('city_schedules', {})
        mode = campaign_data.get('campaign_mode', 'MULTI_VEHICLE_CUSTOM')
        all_vids = [campaign_data.get('vehicle_id')] + [av.get('vehicle_id') for av in campaign_data.get('additional_vehicles', [])]
        num_vehicles = len([v for v in all_vids if v])
        meta = city_periods.get('__meta__', {})
        is_shared = meta.get('shared_mode', False) if isinstance(meta, dict) else False
        total_campaign_hours = 0
        total_peak_hours = 0
        total_active_days_set = set()
        v_list = all_vids if not is_shared else ["SHARED_V_PLACEHOLDER"]
        for v_entry in v_list:
            v_day_hours, v_day_peak = {}, {}
            itinerary_source = {c: city_periods.get(c, []) for c in cities if c != '__meta__'} if is_shared else city_periods.get(v_entry, {})
            schedules_source = city_schedules if is_shared else city_schedules.get(v_entry, {})
            if not isinstance(itinerary_source, dict): continue
            for city_name, periods in itinerary_source.items():
                c_schedule = schedules_source.get(city_name, {})
                if isinstance(periods, dict): periods = [periods]
                if not isinstance(periods, list): continue
                for period in periods:
                    if isinstance(period, list) and len(period) > 0: period = period[0]
                    if not isinstance(period, dict): continue
                    start, end = period.get('start'), period.get('end')
                    if not start or not end: continue
                    if isinstance(start, str): start = datetime.date.fromisoformat(start[:10])
                    if isinstance(end, str): end = datetime.date.fromisoformat(end[:10])
                    current = start
                    while current <= end:
                        date_str = current.strftime('%Y-%m-%d')
                        total_active_days_set.add(date_str)
                        day_data = c_schedule.get(date_str)
                        h_str = day_data.get('hours', campaign_data['daily_hours']) if (not day_data or day_data.get('active', True)) else "00:00-00:00"
                        metrics = self._parse_daily_hours(h_str)
                        v_day_hours[date_str] = max(v_day_hours.get(date_str, 0), metrics['hours'])
                        v_day_peak[date_str] = max(v_day_peak.get(date_str, 0), metrics['peak_hours'])
                        current += datetime.timedelta(days=1)
            total_campaign_hours += sum(v_day_hours.values()) * (num_vehicles if is_shared else 1)
            total_peak_hours += sum(v_day_peak.values()) * (num_vehicles if is_shared else 1)
        total_active_days = len(total_active_days_set)
        # Average per vehicle
        v_avg_hours = (total_campaign_hours / num_vehicles) / total_active_days if (total_active_days > 0 and num_vehicles > 0) else 0
        v_avg_peak = (total_peak_hours / num_vehicles) / total_active_days if (total_active_days > 0 and num_vehicles > 0) else 0
        
        return {
            'total_days': total_active_days, 'hours_per_day': v_avg_hours,
            'total_campaign_hours': total_campaign_hours, 'peak_hours_per_day': v_avg_peak,
            'total_peak_hours': total_peak_hours, 'peak_hours_percentage': (v_avg_peak / v_avg_hours * 100) if v_avg_hours > 0 else 0,
            'has_custom_schedule': bool(city_schedules) or bool(campaign_data.get('custom_daily_schedule')),
            'shared_mode': is_shared, 'campaign_mode': mode, 'num_vehicles': num_vehicles
        }

    def _parse_daily_hours(self, hours_str):
        if not hours_str or not isinstance(hours_str, str): return {'hours': 8, 'peak_hours': 0}
        total_hours, total_peak = 0, 0
        for interval in [i.strip() for i in hours_str.split(',')]:
            try:
                if '-' not in interval: continue
                start_time, end_time = interval.split('-')
                start_h, start_m = int(start_time.split(':')[0]), int(start_time.split(':')[1]) if ':' in start_time else 0
                end_h, end_m = int(end_time.split(':')[0]), int(end_time.split(':')[1]) if ':' in end_time else 0
                hours = (end_h - start_h) + (end_m - start_m) / 60
                if hours < 0: hours += 24
                total_hours += hours
                peak_morning, peak_evening = (7, 9), (17, 19)
                c_start_h, c_end_h = start_h + start_m / 60, end_h + end_m / 60
                if c_start_h < peak_morning[1] and c_end_h > peak_morning[0]: total_peak += max(0, min(c_end_h, peak_morning[1]) - max(c_start_h, peak_morning[0]))
                if c_start_h < peak_evening[1] and c_end_h > peak_evening[0]: total_peak += max(0, min(c_end_h, peak_evening[1]) - max(c_start_h, peak_evening[0]))
            except: continue
        return {'hours': total_hours if total_hours > 0 else 8, 'peak_hours': total_peak}

    def _calculate_route_distance(self, speed_kmh, total_hours, stationing_min_per_hour, avg_commute_distance_km=8, known_distance_total=None, custom_daily_distances=None, total_days=1):
        if custom_daily_distances:
            total_km, used_known_distance = sum(custom_daily_distances.values()), True
        elif known_distance_total is not None and known_distance_total > 0:
            total_km, used_known_distance = known_distance_total, True
        else:
            total_km = speed_kmh * (total_hours - (stationing_min_per_hour / 60) * total_hours)
            used_known_distance = False
        effective_driving_hours = total_km / speed_kmh if speed_kmh > 0 else 0
        return {'total_km': int(total_km), 'effective_driving_hours': round(effective_driving_hours, 1), 'route_loops': round(total_km / avg_commute_distance_km, 1) if avg_commute_distance_km > 0 else 0, 'used_known_distance': used_known_distance}

    def _calculate_impressions_by_mode(self, modal_split, daily_traffic, daily_pedestrian, campaign_hours_per_day, total_days, start_date, city_name, spot_duration=10, loop_duration=60, is_exclusive=False, city_schedule=None):
        share_of_voice = 1.0 if is_exclusive else (spot_duration / loop_duration if loop_duration > 0 else 0.16)
        hourly_traffic_base, hourly_pedestrian_base = daily_traffic / 24, daily_pedestrian / 24
        total_campaign_traffic, total_campaign_pedestrian = 0, 0
        current_date, events_encountered = start_date, []
        for i in range(total_days):
            date_str = current_date.strftime('%Y-%m-%d')
            hours_today = campaign_hours_per_day
            if city_schedule and city_schedule.get(date_str):
                day_data = city_schedule[date_str]
                if not day_data.get('active', True): hours_today = 0
                elif day_data.get('hours'): hours_today = self._parse_daily_hours(day_data['hours'])['hours']
            if hours_today > 0:
                t_mult, p_mult, event_name = self.city_manager.get_event_multipliers(city_name, current_date)
                if event_name and event_name not in events_encountered: events_encountered.append(event_name)
                total_campaign_traffic += hourly_traffic_base * hours_today * t_mult
                total_campaign_pedestrian += hourly_pedestrian_base * hours_today * p_mult
            current_date += datetime.timedelta(days=1)
        auto_traffic, cycling_traffic, walking_traffic = total_campaign_traffic * (modal_split.get('auto', 35) / 100), total_campaign_traffic * (modal_split.get('cycling', 4) / 100), total_campaign_pedestrian * (modal_split.get('walking', 27) / 100)
        visibility_factor = 1.0 if is_exclusive else 0.7
        auto_impressions, pedestrian_impressions = auto_traffic * 1.65 * visibility_factor * share_of_voice, (walking_traffic + cycling_traffic) * visibility_factor * share_of_voice
        return {'auto': int(auto_impressions), 'pedestrian': int(pedestrian_impressions), 'total': int(auto_impressions + pedestrian_impressions), 'events': events_encountered, 'share_of_voice': share_of_voice}

    def _calculate_ots_and_reach(self, total_impressions, route_loops, active_population):
        coverage_factor = min(route_loops / 10, 1.0)
        reach = int(active_population * 0.6 * coverage_factor)
        return {'reach': reach, 'ots': round(total_impressions / reach, 1) if reach > 0 else 1.0}

    def get_total_impressions_data(self, data, duration_metrics):
        """Standardized aggregation of impressions across all cities and vehicles"""
        total_impressions_data = {'auto': 0, 'pedestrian': 0, 'total': 0, 'events': []}
        
        # Robust vehicle counting
        all_vids = []
        if data.get('vehicle_id'): all_vids.append(data['vehicle_id'])
        for av in data.get('additional_vehicles', []):
            if isinstance(av, dict): 
                vid = av.get('vehicle_id') or av.get('id')
                if vid: all_vids.append(vid)
            elif isinstance(av, (str, int)): all_vids.append(str(av))
        all_vids = list(set(all_vids))  # Ensure uniqueness
        v_count = len([v for v in all_vids if v]) or 1
        
        meta = data.get('city_periods', {}).get('__meta__', {})
        shared_mode = meta.get('shared_mode', True)
        cities = data.get('cities', []) or ([data['city']] if data.get('city') else [])
        default_modal_split = {'auto': 35, 'walking': 27, 'cycling': 4, 'public_transport': 34}
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
                    c_start = datetime.date.fromisoformat(period['start'][:10]) if isinstance(period.get('start'), str) else period.get('start')
                    c_end = datetime.date.fromisoformat(period['end'][:10]) if isinstance(period.get('end'), str) else period.get('end')
                    if not c_start or not c_end: continue
                    city_profile = self.city_manager.get_city_data_for_period(city_name, c_start)
                    if not city_profile: continue
                    inc = self._calculate_impressions_by_mode(city_profile.get('modal_split', default_modal_split), city_profile.get('daily_traffic_total', 50000), city_profile.get('daily_pedestrian_total', 50000), duration_metrics['hours_per_day'], (c_end - c_start).days+1, c_start, city_name, spot_duration=data.get('spot_duration', 10), loop_duration=data.get('loop_duration', 60), is_exclusive=data.get('is_exclusive', False), city_schedule=c_schedule)
                    total_impressions_data['auto'] += inc['auto']; total_impressions_data['pedestrian'] += inc['pedestrian']; total_impressions_data['total'] += inc['total']
                    for ev in inc['events']:
                        if ev not in total_impressions_data['events']: total_impressions_data['events'].append(ev)
        else:
            v_count = len([v for v in all_vids if v]) or 1
            for city_name in cities:
                all_periods = data.get('city_periods', {})
                periods = all_periods.get(city_name, [{'start': data['start_date'], 'end': data['end_date']}])
                if isinstance(periods, dict): periods = [periods]
                all_schedules = data.get('city_schedules', {})
                c_schedule = all_schedules.get(city_name)
                for period in periods:
                    c_start = datetime.date.fromisoformat(period['start'][:10]) if isinstance(period.get('start'), str) else period.get('start')
                    c_end = datetime.date.fromisoformat(period['end'][:10]) if isinstance(period.get('end'), str) else period.get('end')
                    if not c_start or not c_end: continue
                    city_profile = self.city_manager.get_city_data_for_period(city_name, c_start)
                    if not city_profile: continue
                    inc = self._calculate_impressions_by_mode(city_profile.get('modal_split', default_modal_split), city_profile.get('daily_traffic_total', 50000), city_profile.get('daily_pedestrian_total', 50000), duration_metrics['hours_per_day'], (c_end - c_start).days+1, c_start, city_name, spot_duration=data.get('spot_duration', 10), loop_duration=data.get('loop_duration', 60), is_exclusive=data.get('is_exclusive', False), city_schedule=c_schedule)
                    total_impressions_data['auto'] += inc['auto'] * v_count; total_impressions_data['pedestrian'] += inc['pedestrian'] * v_count; total_impressions_data['total'] += inc['total'] * v_count
                    for ev in inc['events']:
                        if ev not in total_impressions_data['events']: total_impressions_data['events'].append(ev)
        return total_impressions_data

    def _generate_campaign_pdf(self, data, output_path):
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle, Image, Paragraph, Spacer
        cities = data.get('cities', []) or ([data['city']] if data.get('city') else [])
        meta = data.get('city_periods', {}).get('__meta__', {})
        shared_mode = meta.get('shared_mode', True)
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        
        client_name = remove_diacritics(data.get('client_name', 'Unnamed Client'))
        campaign_name = remove_diacritics(data.get('campaign_name', 'Unnamed Campaign'))
        
        # --- Header & Logo ---
        settings = self.company_settings.get_settings()
        if settings:
            logo_path = settings.get('logo_path')
            if logo_path and os.path.exists(logo_path):
                logo = Image(logo_path, width=1.5*inch, height=0.8*inch)
                logo.hAlign = 'LEFT'
                story.append(logo)
            comp_name = settings.get('name', '')
            if comp_name:
                header_text = f"<b>{remove_diacritics(comp_name)}</b>"
                if settings.get('registration_number'): header_text += f" | {settings['registration_number']}"
                story.append(Paragraph(header_text, ParagraphStyle('CompanyHeader', parent=self.styles['Normal'], fontSize=8, textColor=colors.grey)))
                story.append(Spacer(1, 12))

        # --- Title ---
        intro_tmpl = random.choice(ReportTemplates.INTRO)
        story.append(Paragraph(remove_diacritics(intro_tmpl.format(client_name=client_name)), self.styles['Normal']))
        story.append(Spacer(1, 12))
        
        story.append(Paragraph(f"<b>" + remove_diacritics(_("Campaign Report") + f": {campaign_name}</b>"), self.styles['Title']))
        story.append(Spacer(1, 12))

        # --- Identification Table ---
        city_display = remove_diacritics(data.get('display_cities', ", ".join(cities) if cities else 'Unknown'))
        
        # Get duration metrics early for the header
        duration_metrics = self._calculate_multi_city_metrics(data) if ('city_periods' in data or 'city_schedules' in data) else self._calculate_campaign_duration(data['start_date'], data['end_date'], data['daily_hours'], data.get('custom_daily_schedule'))
        
        # Determine Mode Label
        mode_key = data.get('campaign_mode', 'SINGLE_VEHICLE_CITY')
        mode_label = CAMPAIGN_MODES.get(mode_key, {}).get('label', mode_key)
        
        # Determine Vehicle/Driver info
        v_reg = "N/A"
        d_name = "N/A"
        if data.get('vehicle_id'):
            v = self.vehicle_manager.get_vehicle(data['vehicle_id'])
            if v:
                name, reg = v.get('name', ''), v.get('registration', '')
                if name and reg: v_reg = f"{name} ({reg})"
                else: v_reg = name or reg or "N/A"
                # Driver from vehicle
                if v.get('driver_name'):
                    d_name = v['driver_name']
                elif v.get('driver_id'):
                    d = self.driver_manager.get_driver(v['driver_id'])
                    if d: d_name = d.get('name', 'N/A')
        
        # Primary driver if specified in campaign
        if data.get('driver_id'):
            d = self.driver_manager.get_driver(data['driver_id'])
            if d: d_name = d.get('name', 'N/A')

        # Prepare tables with wrapping Paragraphs to prevent overlaps
        id_data = [
            [Paragraph(f"<b>{remove_diacritics(_('Client'))}:</b>", self.styles['Normal']), Paragraph(client_name, self.styles['Normal'])],
            [Paragraph(f"<b>{remove_diacritics(_('Campaign'))}:</b>", self.styles['Normal']), Paragraph(campaign_name, self.styles['Normal'])],
            [Paragraph(f"<b>{remove_diacritics(_('PO Number'))}:</b>", self.styles['Normal']), Paragraph(str(data.get('po_number', '-')), self.styles['Normal'])],
            [Paragraph(f"<b>{remove_diacritics(_('City'))}:</b>", self.styles['Normal']), Paragraph(city_display, self.styles['Normal'])],
            [Paragraph(f"<b>{remove_diacritics(_('Period'))}:</b>", self.styles['Normal']), Paragraph(f"{data['start_date'].strftime('%d.%m.%Y')} - {data['end_date'].strftime('%d.%m.%Y')} ({duration_metrics['total_days']} zile)", self.styles['Normal'])],
            [Paragraph(f"<b>{remove_diacritics(_('Daily Hours'))}:</b>", self.styles['Normal']), Paragraph(f"{data['daily_hours']} (Medie: {duration_metrics['hours_per_day']:.1f} h/zi)", self.styles['Normal'])],
            [Paragraph(f"<b>{remove_diacritics(_('Vehicle'))}:</b>", self.styles['Normal']), Paragraph(remove_diacritics(v_reg), self.styles['Normal'])],
            [Paragraph(f"<b>{remove_diacritics(_('Driver'))}:</b>", self.styles['Normal']), Paragraph(remove_diacritics(d_name), self.styles['Normal'])],
            [Paragraph(f"<b>{remove_diacritics(_('Campaign Mode'))}:</b>", self.styles['Normal']), Paragraph(remove_diacritics(mode_label), self.styles['Normal'])],
            [Paragraph(f"<b>{remove_diacritics(_('Objective'))}:</b>", self.styles['Normal']), Paragraph(remove_diacritics(_("Estimare trafic pietonal si auto expus, corelat cu date demografice si mobilitate urbana.")), self.styles['Normal'])]
        ]
        
        t_id = Table(id_data, colWidths=[1.8*inch, 4.7*inch])
        t_id.setStyle(TableStyle([
            # ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'), # Paragraph handles the bold
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 6)
        ]))
        story.append(t_id)
        story.append(Spacer(1, 24))

        # --- Section 1: Context Demografic ---
        story.append(Paragraph("<b>1. " + remove_diacritics(_("Demographic Context & Urban Mobility")) + "</b>", self.styles['Heading2']))
        pop_active = int(data['population'] * data['active_population_pct'] / 100)
        demo_tmpl = random.choice(ReportTemplates.DEMOGRAPHICS)
        story.append(Paragraph(remove_diacritics(demo_tmpl.format(
            city_display=city_display,
            population=data['population'],
            pop_active=pop_active,
            active_pct=data['active_population_pct']
        )), self.styles['Normal']))
        story.append(Spacer(1, 12))

        # --- Modal Split Chart in Section 1 ---
        weighted_modal_split = {'auto': 0, 'walking': 0, 'cycling': 0, 'public_transport': 0}
        total_pop_ms = 0
        for city in cities:
            cp = self.city_manager.get_city_data_for_period(city, data['start_date'])
            p_ms = cp.get('population', 100000) if cp else 100000
            total_pop_ms += p_ms
            ms_city = cp.get('modal_split', {'auto': 35, 'walking': 27, 'cycling': 4, 'public_transport': 34}) if cp else {'auto': 35, 'walking': 27, 'cycling': 4, 'public_transport': 34}
            for m in ms_city: weighted_modal_split[m] += ms_city.get(m, 0) * p_ms
        
        if total_pop_ms > 0:
            final_ms = {remove_diacritics(m.capitalize().replace('_', ' ')): v/total_pop_ms for m, v in weighted_modal_split.items()}
            ms_chart = self.create_pie_chart(final_ms, remove_diacritics(_("Repartitie Modal Split (Transport)")))
            if ms_chart:
                img_ms = Image(ms_chart, width=3.5*inch, height=3.5*inch)
                img_ms.hAlign = 'CENTER'
                story.append(img_ms)
                story.append(Spacer(1, 12))

        # --- Section 2: Estimari Trafic ---
        story.append(Paragraph("<b>2. " + remove_diacritics(_("Traffic Estimates (Campaign Interval)")) + "</b>", self.styles['Heading2']))
        story.append(Paragraph("<b>" + remove_diacritics(_("Global Metrics")) + "</b>", self.styles['Heading3']))
        
        impressions = self.get_total_impressions_data(data, duration_metrics)
        avg_commute_distance = 8 # Default
        if cities:
            total_dist = 0
            for city in cities:
                cp = self.city_manager.get_city_data_for_period(city, data['start_date'])
                total_dist += (cp.get('avg_commute_distance_km', 8) if cp else 8)
            avg_commute_distance = total_dist / len(cities)

        route_metrics = self._calculate_route_distance(
            data.get('vehicle_speed_kmh', 25), 
            duration_metrics['total_campaign_hours'], 
            data.get('stationing_min_per_hour', 15), 
            avg_commute_distance, 
            data.get('known_distance_total'), 
            data.get('custom_daily_distances'), 
            duration_metrics['total_days']
        )
        audience_metrics = self._calculate_ots_and_reach(impressions['total'], route_metrics['route_loops'], pop_active)
        reach, ots = audience_metrics['reach'], audience_metrics['ots']

        metrics_data = [
            [Paragraph(f"<b>{remove_diacritics(_('Metric'))}</b>", self.styles['Normal']), Paragraph(f"<b>{remove_diacritics(_('Value'))}</b>", self.styles['Normal']), Paragraph(f"<b>{remove_diacritics(_('Description'))}</b>", self.styles['Normal'])],
            [Paragraph(remove_diacritics(_("Total Impressions")), self.styles['Normal']), Paragraph(f"{impressions['total']:,}", self.styles['Normal']), Paragraph(remove_diacritics(_("Contacte vizuale brute (Auto + Pietonal) ajustate cu factori de vizibilitate.")), self.styles['Normal'])],
            [Paragraph(remove_diacritics(_("Total Hours")), self.styles['Normal']), Paragraph(f"{duration_metrics['total_campaign_hours']:.1f}", self.styles['Normal']), Paragraph(remove_diacritics(_("Timp net de emisie, excluzand stationarea si timpii morti.")), self.styles['Normal'])],
            [Paragraph(remove_diacritics(_("Avg Speed")), self.styles['Normal']), Paragraph(f"{data.get('vehicle_speed_kmh', 25)} km/h", self.styles['Normal']), Paragraph(remove_diacritics(_("Viteza medie de croaziera aliniata cu indicii de mobilitate PMUD.")), self.styles['Normal'])],
            [Paragraph(remove_diacritics(_("Stationing")), self.styles['Normal']), Paragraph(f"{data.get('stationing_min_per_hour', 15)} min/h", self.styles['Normal']), Paragraph(remove_diacritics(_("Maximizes exposure in high-footfall areas (20-30% OTS boost).")), self.styles['Normal'])],
            [Paragraph(remove_diacritics(_("Potential Reach")), self.styles['Normal']), Paragraph(f"{reach:,}", self.styles['Normal']), Paragraph(remove_diacritics(_("Persoane unice expuse (cca. 50-65% din populatia activa).")), self.styles['Normal'])],
            [Paragraph(remove_diacritics(_("OTS")), self.styles['Normal']), Paragraph(f"{ots}", self.styles['Normal']), Paragraph(remove_diacritics(_("Opportunity to See - frecventa medie de vizionare per persoana.")), self.styles['Normal'])]
        ]
        
        t_metrics = Table(metrics_data, colWidths=[1.8*inch, 1.2*inch, 3.5*inch])
        t_metrics.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            # ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), # Paragraph text color is handled in styles
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 6)
        ]))
        story.append(t_metrics)
        story.append(Spacer(1, 24))

        # --- Charts ---
        imp_data = {remove_diacritics(_('Auto')): impressions['auto'], remove_diacritics(_('Pedestrian/Bicycle')): impressions['pedestrian']}
        imp_chart = self.create_pie_chart(imp_data, remove_diacritics(_("Impressions Distribution")))
        if imp_chart:
            story.append(Image(imp_chart, width=4*inch, height=4*inch))
        story.append(Spacer(1, 24))

        # --- Section 4: Conclusions ---
        story.append(Paragraph("<b>4. " + remove_diacritics(_("Conclusions")) + "</b>", self.styles['Heading2']))
        concl_tmpl = random.choice(ReportTemplates.CONCLUSIONS)
        story.append(Paragraph(remove_diacritics(concl_tmpl.format(
            impressions=impressions['total'], 
            city_display=city_display, 
            stationing=data.get('stationing_min_per_hour', 15)
        )), self.styles['Normal']))
        
        story.append(Spacer(1, 24))
        story.append(Paragraph("<i>" + remove_diacritics(_("*This report is based on statistical estimates and average traffic data.")) + "</i>", 
                             ParagraphStyle('Note', parent=self.styles['Normal'], fontSize=8, textColor=colors.grey)))

        # Add Methodology Notes
        self._append_methodology_notes(story)
        
        doc.build(story)
        
        return {
            'total_impressions': impressions['total'],
            'auto_impressions': impressions['auto'],
            'pedestrian_impressions': impressions['pedestrian'],
            'reach': reach,
            'ots': ots,
            'total_hours': duration_metrics['total_campaign_hours'],
            'active_days': duration_metrics['total_days'],
            'num_vehicles': duration_metrics.get('num_vehicles', 1),
            'avg_hours_per_day': duration_metrics['hours_per_day']
        }

    def _append_methodology_notes(self, story):
        """Adds a section explaining the report calculation logic"""
        story.append(PageBreak())
        story.append(Paragraph(remove_diacritics(_("Anexe si Metodologie de Calcul")), self.styles['Heading2']))
        story.append(Spacer(1, 12))
        
        methodology_text = [
            ("<b>1. " + remove_diacritics(_("Calculul Impresiilor")) + "</b>", 
             remove_diacritics(_("Formula: Auto (Trafic * 1.65 ocupanti * Factor Vizibilitate * SOV) si Pietoni ((Trafic + Biciclisti) * Factor Vizibilitate * SOV). Date baza: INS, Eurostat si PMUD local (Planul de Mobilitate Urbana Durabila)."))),
            ("<b>2. " + remove_diacritics(_("Reach si OTS")) + "</b>", 
             remove_diacritics(_("Reach (Acoperire Unica): 50-65% din Populatia Activa, bazat pe rata de unicitate a traseului. OTS (Opportunity To See): Frecventa medie (Impresii/Reach), ridicata prin congestie si stationare (20-30% boost)."))),
            ("<b>3. " + remove_diacritics(_("Mobilitate si Distante")) + "</b>", 
             remove_diacritics(_("Distanta: Calculata la 20 km/h (PMUD max). Ore Efective: Ore Totale - Stationare (10 min/ora). Bucle Traseu: Distanta Totala / 8km (distanta medie naveta urbana)."))),
            ("<b>4. " + remove_diacritics(_("Factori de Eficienta")) + "</b>", 
             remove_diacritics(_("Share of Voice (SOV): Raport Spot/Loop. Factor Vizibilitate: 0.7 (Standard) vs 1.0 (Exclusiv). Congestia (LOS D-F pe artere principale) prelungeste expunerea si creste gradul de observare."))),
            ("<b>5. " + remove_diacritics(_("Sursa si Validare")) + "</b>", 
             remove_diacritics(_("Estimari statistice bazate pe PMUD (2021-2030), Numbeo Traffic Index si date flux orar (CNAIR). Proof of Play auditabil prin log-uri VnNox si senzoristica GPS a vehiculului Mobile DOOH.")))
        ]
        
        for title, desc in methodology_text:
            story.append(Paragraph(remove_diacritics(title), self.styles['Normal']))
            story.append(Paragraph(remove_diacritics(desc), self.styles['Normal']))
            story.append(Spacer(1, 8))
