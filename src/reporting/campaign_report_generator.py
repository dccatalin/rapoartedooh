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
        self.report_storage = ReportStorage()

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
        client_name, campaign_name = remove_diacritics(data['client_name']), remove_diacritics(data['campaign_name'])
        settings = self.company_settings.get_settings()
        if settings:
            logo_path = settings.get('logo_path')
            if logo_path and os.path.exists(logo_path):
                logo = Image(logo_path, width=1.5*inch, height=0.8*inch); logo.hAlign = 'LEFT'; story.append(logo); story.append(Spacer(1, 6))
            comp_name = settings.get('name', '')
            if comp_name:
                header_text = f"<b>{comp_name}</b>"
                if settings.get('registration_number'): header_text += f" | {settings['registration_number']}"
                if settings.get('address'): header_text += f"<br/>{settings['address']}"
                story.append(Paragraph(header_text, ParagraphStyle('CompanyHeader', parent=self.styles['Normal'], fontSize=8, textColor=colors.grey)))
                story.append(Spacer(1, 12))
        intro_tmpl = random.choice(ReportTemplates.INTRO)
        story.append(Paragraph(remove_diacritics(intro_tmpl.format(client_name=client_name)), self.styles['Normal']))
        story.append(Spacer(1, 12))
        city_display = remove_diacritics(data.get('display_cities', data.get('city', 'Unknown')))
        story.append(Paragraph(f"<b>" + remove_diacritics(_("Campaign Report") + f": {campaign_name}</b>"), self.styles['Title']))
        story.append(Spacer(1, 12))
        data_table = [[_("Client") + ":", client_name], [_("Campaign") + ":", campaign_name], [_("PO Number") + ":", str(data.get('po_number', '-'))], [_("City") + ":", city_display], [_("Period") + ":", f"{data['start_date'].strftime('%d.%m.%Y')} - {data['end_date'].strftime('%d.%m.%Y')}"], [_("Daily Hours") + ":", str(data['daily_hours'])]]
        t = Table(data_table, colWidths=[1.5*inch, 5*inch]); t.setStyle(TableStyle([('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke), ('PADDING', (0,0), (-1,-1), 6)])); story.append(t); story.append(Spacer(1, 24))
        duration_metrics = self._calculate_multi_city_metrics(data) if ('city_periods' in data or 'city_schedules' in data) else self._calculate_campaign_duration(data['start_date'], data['end_date'], data['daily_hours'], data.get('custom_daily_schedule'))
        info_style = self.styles['Normal']
        story.append(Paragraph(f"<b>{_('Report Date')}:</b> {datetime.date.today().strftime('%d %B %Y')}", info_style))
        story.append(Paragraph(f"<b>{_('Campaign Period')}:</b> {data['start_date'].strftime('%d')} - {data['end_date'].strftime('%d %B %Y')} ({_('Total active days')}: {duration_metrics['total_days']})", info_style))
        story.append(Paragraph(f"<b>{_('Daily Hours')}:</b> {data['daily_hours']} ({_('Average')}: {duration_metrics['hours_per_day']:.1f} h/day)", info_style))
        story.append(Paragraph(f"<b>{_('Total Exposure Duration')}:</b> {duration_metrics['total_campaign_hours']:.1f} hours", info_style))
        story.append(Spacer(1, 15))
        pop_active = int(data['population'] * data['active_population_pct'] / 100)
        weighted_modal_split = {'auto': 0, 'walking': 0, 'cycling': 0, 'public_transport': 0}
        total_pop, avg_commute_dist = 0, 0
        for city in cities:
            cp = self.city_manager.get_city_data_for_period(city, data['start_date'])
            p = cp.get('population', 100000) if cp else 100000; total_pop += p
            ms = cp.get('modal_split', weighted_modal_split) if cp else {'auto': 35, 'walking': 27, 'cycling': 4, 'public_transport': 34}
            for m in ms: weighted_modal_split[m] += ms.get(m, 0) * p
            avg_commute_dist += (cp.get('avg_commute_distance_km', 8) if cp else 8) * p
        modal_split = {m: int(v / total_pop) for m, v in weighted_modal_split.items()} if total_pop > 0 else {'auto': 35, 'walking': 27, 'cycling': 4, 'public_transport': 34}
        avg_commute_distance = avg_commute_dist / total_pop if total_pop > 0 else 8
        impressions = self.get_total_impressions_data(data, duration_metrics)
        route_metrics = self._calculate_route_distance(data.get('vehicle_speed_kmh', 25), duration_metrics['total_campaign_hours'], data.get('stationing_min_per_hour', 15), avg_commute_distance, data.get('known_distance_total'), data.get('custom_daily_distances'), duration_metrics['total_days'])
        audience_metrics = self._calculate_ots_and_reach(impressions['total'], route_metrics['route_loops'], pop_active)
        reach, ots = audience_metrics['reach'], audience_metrics['ots']
        story.append(Paragraph(_("Global Metrics"), self.styles['Heading2']))
        metrics_data = [[_("Metric"), _("Value"), _("Description")], [_("Total Impressions"), f"{impressions['total']:,}", _("Estimated visual contacts")], [_("Total Hours"), f"{duration_metrics['total_campaign_hours']:.1f}", _("Net broadcasting time")], [_("Reach Potential"), f"{reach:,}", _("Unique viewers")], [_("OTS"), f"{ots}", _("Opportunity to See")]]
        t_metrics = Table(metrics_data, colWidths=[1.5*inch, 1.5*inch, 3.5*inch]); t_metrics.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('PADDING', (0,0), (-1,-1), 6)])); story.append(t_metrics); story.append(Spacer(1, 24))
        imp_data = {_('Auto'): impressions['auto'], _('Pedestrian/Bicycle'): impressions['pedestrian']}
        imp_chart = self.create_pie_chart(imp_data, remove_diacritics(_("Impressions Distribution")))
        if imp_chart: story.append(Image(imp_chart, width=4*inch, height=4*inch))
        story.append(Spacer(1, 24))
        concl_tmpl = random.choice(ReportTemplates.CONCLUSIONS)
        story.append(Paragraph(remove_diacritics(concl_tmpl.format(impressions=impressions['total'], city_display=city_display, stationing=data.get('stationing_min_per_hour', 15))), info_style))
        
        # Add Methodology Notes
        self._append_methodology_notes(story)
        
        doc.build(story)
        
        # Return frozen metrics for the database
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
            ("<b>1. " + _("Sursa Datelor") + "</b>", 
             _("Datele demografice si de trafic sunt preluate din surse publice oficiale (INS, recensamant) si baze de date de mobilitate urbana, actualizate periodic pentru fiecare oras.")),
            ("<b>2. " + _("Calculul Impresiilor (Visual Contacts)") + "</b>", 
             _("Formula: Flux Orar x Ore Activitate x Multiplicatori Evenimente x Factor Vizibilitate x Share of Voice.")),
            ("<b>3. " + _("Factori Corectie") + "</b>", 
             _("Vizibilitatea este ajustata cu un factor de 0.7 (non-exclusiv) sau 1.0 (exclusiv). Share of Voice reprezinta raportul dintre durata de expunere a spotului si durata totala a loop-ului publicitar.")),
            ("<b>4. " + _("Reach si OTS") + "</b>", 
             _("Reach Potential reprezinta numarul estimat de persoane unice expuse mesajului, calculat in functie de populatia activa si frecventa de looping a vehiculului pe traseu. OTS (Opportunity to See) indica numarul mediu de expuneri per persoana unia.")),
            ("<b>5. " + _("Nota Tehnica") + "</b>", 
             _("Toate valorile sunt estimari statistice bazate pe algoritmi de propagare a traficului si nu reprezinta cifre auditate in timp real decat daca este specificat contrariul (Ex: Raport DOOH Auditat)."))
        ]
        
        for title, desc in methodology_text:
            story.append(Paragraph(remove_diacritics(title), self.styles['Normal']))
            story.append(Paragraph(remove_diacritics(desc), self.styles['Normal']))
            story.append(Spacer(1, 8))
