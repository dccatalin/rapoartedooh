import streamlit as st
import datetime
import pandas as pd
import plotly.express as px
import utils
from src.data.driver_manager import DriverManager
from src.data.vehicle_manager import VehicleManager
from src.data.campaign_storage import CampaignStorage

# Initialize
root_dir = utils.init_path()
from src.utils.i18n import _
utils.set_page_config(_("Condică (Timesheet)"), "📒")
utils.inject_custom_css()

# Managers
driver_manager = DriverManager()
vehicle_manager = VehicleManager()
campaign_storage = CampaignStorage()

def get_timesheet_data(start_date, end_date, selected_driver_ids):
    data = []
    
    # Pre-fetch all needed data
    all_drivers = driver_manager.get_all_drivers()
    d_map = {d['id']: d['name'] for d in all_drivers}
    all_v = vehicle_manager.get_all_vehicles()
    v_map = {v['id']: v['name'] for v in all_v}
    v_reg_map = {v['id']: v['registration'] for v in all_v}
    v_drv_map = {v['id']: v.get('driver_id') for v in all_v} # For fallback attribution
    
    # 1. Driver Schedules (Leave, Medical, etc.)
    for d_id in selected_driver_ids:
        schedules = driver_manager.get_driver_schedules(d_id)
        for s in schedules:
            try:
                s_start = datetime.date.fromisoformat(s['start_date']) if isinstance(s['start_date'], str) else s['start_date']
                s_end = datetime.date.fromisoformat(s['end_date']) if isinstance(s['end_date'], str) else s['end_date']
                
                if s_start <= end_date and s_end >= start_date:
                    data.append({
                        'Driver': d_map.get(d_id, _("Unknown")),
                        'Activity': _(s['event_type'].capitalize()),
                        'Start': s_start,
                        'End': s_end,
                        'Resource': "N/A",
                        'Type': _('Leave/Absence'),
                        'Details': s.get('details', ""),
                        'Hours': 0,
                        'HoursInfo': "00:00-24:00"
                    })
            except: pass
                
    # 2. Campaigns (City Periods)
    all_campaigns = campaign_storage.get_all_campaigns()
    for c in all_campaigns:
        c_status = (c.get('status') or 'confirmed').lower()
        
        c_periods = c.get('city_periods', {})
        if not isinstance(c_periods, dict): c_periods = {}
        shared_mode = c_periods.get('__meta__', {}).get('shared_mode', True)
        
        # Vehicles & Drivers in campaign
        v_list = []
        if c.get('vehicle_id'):
            v_list.append({'id': c['vehicle_id'], 'driver_id': c.get('driver_id')})
        for av in c.get('additional_vehicles', []):
            v_list.append({'id': av.get('vehicle_id'), 'driver_id': av.get('driver_id')})
            
        for v_info in v_list:
            v_id = v_info['id']
            # FALLBACK logic: if NO driver is explicitly assigned to this campaign entry,
            # use the driver CURRENTLY assigned to the vehicle in the database.
            drv_id = v_info['driver_id'] or v_drv_map.get(v_id)
            
            if not drv_id or drv_id not in selected_driver_ids: continue
            
            v_name = v_map.get(v_id, _("Unknown"))
            v_reg = v_reg_map.get(v_id, "N/A")
            
            # Extract periods
            periods_to_process = {}
            if shared_mode:
                periods_to_process = {k: v for k, v in c_periods.items() if k != '__meta__'}
            else:
                periods_to_process = c_periods.get(v_id, {})
                
            if not isinstance(periods_to_process, dict): continue
            
            for city, p_list in periods_to_process.items():
                if not isinstance(p_list, list): p_list = [p_list]
                for p in p_list:
                    try:
                        ps_raw = p.get('start')
                        pe_raw = p.get('end')
                        if not ps_raw or not pe_raw: continue
                        
                        ps = datetime.date.fromisoformat(ps_raw) if isinstance(ps_raw, str) else ps_raw
                        pe = datetime.date.fromisoformat(pe_raw) if isinstance(pe_raw, str) else pe_raw
                        
                        if ps <= end_date and pe >= start_date:
                            # CALCULATE ACTUAL HOURS from city_schedules
                            total_hours = 0
                            total_span_hours = 0
                            
                            # Get correct schedule (shared or individual)
                            v_city_sched = (c.get('city_schedules', {}) or {}).get(v_id, {}).get(city, {})
                            if shared_mode:
                                v_city_sched = (c.get('city_schedules', {}) or {}).get(city, {})
                            
                            curr = max(ps, start_date)
                            up_to = min(pe, end_date)
                            while curr <= up_to:
                                day_str = curr.isoformat()
                                if v_city_sched and day_str in v_city_sched:
                                    day_data = v_city_sched[day_str]
                                    if day_data.get('checked', True):
                                        h_str = day_data.get('hours', "09:00-17:00")
                                        # Handle split intervals (e.g. 08:00-12:00, 14:00-18:00)
                                        intervals = [i.strip() for i in h_str.split(',')]
                                        net_h = 0.0
                                        times = []
                                        for interval in intervals:
                                            try:
                                                if '-' not in interval: continue
                                                t1_s, t2_s = interval.split('-')
                                                H1, M1 = map(int, t1_s.split(':')) if ':' in t1_s else (int(t1_s), 0)
                                                H2, M2 = map(int, t2_s.split(':')) if ':' in t2_s else (int(t2_s), 0)
                                                start_num = H1 + M1/60.0
                                                end_num = H2 + M2/60.0
                                                if end_num < start_num: end_num += 24.0
                                                net_h += (end_num - start_num)
                                                times.append(start_num)
                                                times.append(end_num)
                                            except: continue
                                        
                                        if times:
                                            total_hours += net_h
                                            # Calculation of span
                                            day_span = max(times) - min(times)
                                            total_span_hours += day_span
                                        else:
                                            total_hours += 8
                                            total_span_hours += 8
                                curr += datetime.timedelta(days=1)
                            
                            data.append({
                                'Driver': d_map.get(drv_id, _("Unknown")),
                                'Activity': f"📍 {city} ({c['campaign_name']})",
                                'Start': ps,
                                'End': pe,
                                'Resource': f"{v_name} ({v_reg})",
                                'Type': _('Campaign'),
                                'Status': _(c_status.capitalize()),
                                'Details': _("Camp.") + f": {round(total_hours, 1)}h | " + _("Pontaj") + f": {round(total_span_hours, 1)}h",
                                'Hours': round(total_hours, 1),
                                'Worked Hours': round(total_span_hours, 1),
                                'HoursInfo': v_city_sched
                            })
                    except: pass

    # 3. Transits (Campaign & Global)
    for c in all_campaigns:
        c_status = (c.get('status') or 'confirmed').lower()
        
        for tp in c.get('transit_periods', []):
            tp_vid = tp.get('vehicle_id')
            # Fallback logic for transits too
            drv_id = None
            if c.get('vehicle_id') == tp_vid: drv_id = c.get('driver_id') or v_drv_map.get(tp_vid)
            else:
                for av in c.get('additional_vehicles', []):
                    if av.get('vehicle_id') == tp_vid:
                        drv_id = av.get('driver_id') or v_drv_map.get(tp_vid)
                        break
            
            if drv_id and drv_id in selected_driver_ids:
                try:
                    ts = datetime.date.fromisoformat(tp['start']) if isinstance(tp['start'], str) else tp['start']
                    te = datetime.date.fromisoformat(tp['end']) if isinstance(tp['end'], str) else tp['end']
                    
                    if ts <= end_date and te >= start_date:
                        # Numeric hours, default to 8 if not set
                        try:
                            h_val = float(tp.get('hours', 8.0))
                            if h_val <= 0: h_val = 8.0
                        except:
                            h_val = 8.0

                        data.append({
                            'Driver': d_map.get(drv_id, _("Unknown")),
                            'Activity': f"🚚 {tp.get('origin')} ➡ {tp.get('destination')} ({c['campaign_name']})",
                            'Start': ts,
                            'End': te,
                            'Resource': f"{v_map.get(tp_vid)} ({v_reg_map.get(tp_vid)})",
                            'Type': _('Transit'),
                            'Details': tp.get('details', ""),
                            'Hours': h_val,
                            'HoursInfo': tp.get('hours', "00:00-24:00")
                        })
                except: pass
                    
    # Global Transits
    raw_schs = vehicle_manager.get_vehicle_schedules()
    for s in raw_schs:
        vid = s['vehicle_id']
        drv_id = v_drv_map.get(vid)
        
        if drv_id and drv_id in selected_driver_ids:
            try:
                ts = s['start']
                te = s['end']
                if ts <= end_date and te >= start_date:
                    data.append({
                        'Driver': d_map.get(drv_id, _("Unknown")),
                        'Activity': f"🚛 {_(s['type'].capitalize())}: {s.get('origin', '')} ➡ {s.get('destination', '')}",
                        'Start': ts,
                        'End': te,
                        'Resource': f"{v_map.get(vid)} ({v_reg_map.get(vid)})",
                        'Type': _('Vehicle Event'), # Treat as event
                        'Details': s.get('details', ""),
                        'Hours': 8.0, # Default for global vehicle events
                        'HoursInfo': s.get('hours', "00:00-24:00")
                    })
            except: pass
                
    return data

def main():
    st.title("📒 " + _("Condică (Timesheet)"))
    
    # --- Settings for Debug ---
    from src.data.company_settings import CompanySettings
    cs_mgr = CompanySettings()
    c_settings = cs_mgr.get_settings()
    debug_mode = c_settings.get('debug_mode', False)

    # --- Main Filters ---
    with st.container(border=True):
        st.subheader("🔍 " + _("Filters"))
        f_col1, f_col2, f_col3 = st.columns([1, 1, 2])
        
        today = datetime.date.today()
        preset_opts = [_("Current Month"), _("Last 3 Months"), _("Current Year"), _("Custom Range")]
        preset = f_col1.selectbox(_("Period"), preset_opts)
        
        if preset == _("Current Month"):
            start_date = today.replace(day=1)
            end_date = (today.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
        elif preset == _("Last 3 Months"):
            start_date = today - datetime.timedelta(days=90)
            end_date = today
        elif preset == _("Current Year"):
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
        else:
            sc1, sc2 = f_col1.columns(2)
            start_date = sc1.date_input(_("From"), today.replace(day=1))
            end_date = sc2.date_input(_("To"), today)

        all_drivers = driver_manager.get_all_drivers()
        if not all_drivers:
            st.warning(_("No drivers found."))
            return
            
        d_opts = {d['id']: d['name'] for d in all_drivers}
        selected_drv_ids = f_col2.multiselect(_("Select Drivers"), options=list(d_opts.keys()), default=list(d_opts.keys()), format_func=lambda x: d_opts[x])

    if not selected_drv_ids:
        st.info(_("Select at least one driver to see activity."))
        return

    # --- Data Processing ---
    timesheet_data = get_timesheet_data(start_date, end_date, selected_drv_ids)

    # --- Debug Info (Conditional) ---
    if debug_mode:
        with st.expander("🔍 Debug Info"):
            st.write(f"Filter: {start_date} -> {end_date}")
            st.write(f"Drivers: {len(selected_drv_ids)}")
            st.write(f"Events: {len(timesheet_data)}")
    
    if not timesheet_data:
        st.info(_("No activity found for the selected filters."))
        return
        
    df = pd.DataFrame(timesheet_data)
    # Ensure HoursInfo is formatted nicely for export
    if 'HoursInfo' in df.columns:
        def format_hours_info(val):
            if isinstance(val, str):
                # Try to see if it's a string representation of a dict
                if val.strip().startswith('{'):
                    try:
                        import ast
                        val_dict = ast.literal_eval(val)
                        if isinstance(val_dict, dict):
                            # Extract unique hours
                            all_h = set()
                            for k, v in val_dict.items():
                                if isinstance(v, dict) and 'hours' in v:
                                    all_h.add(v['hours'])
                            if len(all_h) == 1: return list(all_h)[0]
                            elif len(all_h) > 1: return ", ".join(sorted(list(all_h)))
                            else: return "09:00-17:00"
                    except: pass
                return val
            elif isinstance(val, dict):
                 # Extract unique hours
                all_h = set()
                for k, v in val.items():
                    if isinstance(v, dict) and 'hours' in v:
                        all_h.add(v['hours'])
                if len(all_h) == 1: return list(all_h)[0]
                elif len(all_h) > 1: return ", ".join(sorted(list(all_h)))
                else: return "09:00-17:00"
            return str(val)

        df['HoursInfo'] = df['HoursInfo'].apply(format_hours_info)
        df['HoursInfo'] = df['HoursInfo'].astype(str)
    
    # --- Summary Metrics ---
    total_days = (end_date - start_date).days + 1
    leave_days = df[df['Type'] == _('Leave/Absence')].shape[0]
    campaign_days = df[df['Type'] == _('Campaign')].shape[0]
    
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric(_("Days"), total_days)
    m2.metric(_("Campaign") + " (" + _("Events") + ")", campaign_days)
    m3.metric(_("Campaign Hours"), round(df['Hours'].sum(), 1))
    m4.metric(_("Worked Hours") + " (Pontaj)", round(df.get('Worked Hours', df['Hours']).sum(), 1))
    m5.metric(_("Transit") + " (" + _("Events") + ")", df[df['Type'] == _('Transit')].shape[0])
    
    if not df[df['Type'] == _('Vehicle Event')].empty:
        st.metric(_("Vehicle Events"), df[df['Type'] == _('Vehicle Event')].shape[0])

    # --- Tabs ---
    tab_list, tab_timeline = st.tabs(["📋 " + _("Activity List"), "📊 " + _("Activity Timeline")])

    with tab_timeline:
        st.subheader("📊 " + _("Activity Timeline"))
        
        # Build granular plot data using standardized utility
        plot_items = []
        for row in timesheet_data:
            h_info = row.get('HoursInfo', "00:00-24:00")
            # For non-hours items like Leave, we use the row's Start/End directly if get_granular returns empty
            intervals = utils.get_granular_intervals(row['Start'], row['End'], h_info)
            
            if not intervals:
                # Fallback for full day events or items that didn't match get_granular
                d_p = row.copy()
                d_p['Finish'] = row['End'] + datetime.timedelta(days=1)
                plot_items.append(d_p)
            else:
                for g_s, g_e in intervals:
                    # STRICT FILTERING BY DATE
                    g_s_date = utils.ensure_date(g_s)
                    g_e_date = utils.ensure_date(g_e)
                    if not (g_s_date <= end_date and g_e_date >= start_date):
                        continue
                        
                    d_p = row.copy()
                    d_p['Start'] = g_s
                    d_p['Finish'] = g_e
                    plot_items.append(d_p)
        
        if plot_items:
            df_plot = pd.DataFrame(plot_items)
            
            fig = px.timeline(
                df_plot, 
                x_start="Start", 
                x_end="Finish", 
                y="Driver", 
                color="Type",
                hover_data=["Activity", "Resource"],
                color_discrete_map={
                    _('Leave/Absence'): '#FF4B4B',
                    _('Campaign'): '#0068C9',
                    _('Transit'): '#29B09D',
                    _('Global Event'): '#839192',
                    _('Vehicle Event'): '#CB4335'
                },
                category_orders={"Driver": sorted(list(d_opts.values()))}
            )
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(height=450, margin=dict(l=0, r=0, t=30, b=0))
            
            # FORCE X-AXIS RANGE
            fig.update_xaxes(range=[start_date, end_date])
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(_("No timeline data found for the selected filters."))

    with tab_list:
        # Pre-fetch for daily breakdown
        all_campaigns = campaign_storage.get_all_campaigns()
        all_v = vehicle_manager.get_all_vehicles()
        v_drv_map = {v['id']: v.get('driver_id') for v in all_v}

        # --- Detailed Table ---
        st.subheader("📋 Detalii Activitate")
        df['Durata (Zile)'] = df.apply(lambda row: (row['End'] - row['Start']).days + 1, axis=1)
        df_sorted = df.sort_values(['Driver', 'Start'], ascending=[True, False])
        
        # Pagination for Detailed Table
        t_items = len(df_sorted)
        p_col1, p_col2 = st.columns([2, 1])
        t_page_size = p_col2.selectbox(_("Rows per page"), [10, 20, 50, 100], index=0, key="t_page_size")
        t_total_pages = max(1, (t_items + t_page_size - 1) // t_page_size)
        t_page = p_col1.number_input(_("Page") + f" (1-{t_total_pages})", min_value=1, max_value=t_total_pages, value=1, key="t_page")
        
        t_start = (t_page - 1) * t_page_size
        t_end = min(t_start + t_page_size, t_items)
        st.dataframe(df_sorted.iloc[t_start:t_end], use_container_width=True)

        # --- Daily Breakdown ---
        st.divider()
        st.subheader("🗓️ Raport Zilnic (Ore Lucrate)")
        
        daily_rows = []
        for d_id in selected_drv_ids:
            drv_name = d_opts[d_id]
            curr = start_date
            while curr <= end_date:
                day_hours = 0
                day_activities = []
                
                # 1. Activities from pre-calculated data
                for item in timesheet_data:
                    if item['Driver'] == drv_name and item['Start'] <= curr <= item['End']:
                        if item['Type'] == 'Transit':
                            day_hours += float(item.get('Hours', 8.0))
                            day_activities.append(item['Activity'])
                        elif item['Type'] == 'Leave/Absence':
                            day_activities.append(f"🏖️ {item['Activity']}")
                
                # 2. Campaign Schedules
                for c in all_campaigns:
                    if (c.get('status') or 'confirmed').lower() == 'draft': continue
                    v_ids = []
                    if (c.get('driver_id') or v_drv_map.get(c.get('vehicle_id'))) == d_id:
                        v_ids.append(c.get('vehicle_id'))
                    for av in c.get('additional_vehicles', []):
                        if (av.get('driver_id') or v_drv_map.get(av.get('vehicle_id'))) == d_id:
                            v_ids.append(av.get('vehicle_id'))
                    
                    if not v_ids: continue
                    c_periods = c.get('city_periods', {}) or {}
                    shared = c_periods.get('__meta__', {}).get('shared_mode', True)
                    
                    for vid in v_ids:
                        periods_to_check = c_periods if shared else c_periods.get(vid, {})
                        if not isinstance(periods_to_check, dict): continue
                        for city, p_list in periods_to_check.items():
                            if city == '__meta__': continue
                            if not isinstance(p_list, list): p_list = [p_list]
                            for p in p_list:
                                try:
                                    ps = datetime.date.fromisoformat(p['start']) if isinstance(p['start'], str) else p['start']
                                    pe = datetime.date.fromisoformat(p['end']) if isinstance(p['end'], str) else p['end']
                                    if ps <= curr <= pe:
                                        city_sched_data = (c.get('city_schedules', {}) or {}).get(city if shared else vid, {})
                                        if not shared: city_sched_data = city_sched_data.get(city, {})
                                        day_str = curr.isoformat()
                                        if city_sched_data and day_str in city_sched_data:
                                            day_data = city_sched_data[day_str]
                                            if day_data.get('checked', True):
                                                # Explicitly get the string, handle if it's not a string
                                                raw_h = city_sched_data[day_str].get('hours', "09:00-17:00")
                                                h_str = raw_h if isinstance(raw_h, str) else "09:00-17:00"
                                                # For Pontaj (Worked Hours), use SPAN as requested: first to last
                                                intervals = [i.strip() for i in h_str.split(',')]
                                                times = []
                                                for interval in intervals:
                                                    try:
                                                        if '-' not in interval: continue
                                                        t1_s, t2_s = interval.split('-')
                                                        H1, M1 = map(int, t1_s.split(':')) if ':' in t1_s else (int(t1_s), 0)
                                                        H2, M2 = map(int, t2_s.split(':')) if ':' in t2_s else (int(t2_s), 0)
                                                        start_num = H1 + M1/60.0
                                                        end_num = H2 + M2/60.0
                                                        if end_num < start_num: end_num += 24.0
                                                        times.append(start_num)
                                                        times.append(end_num)
                                                    except: continue
                                                
                                                if times:
                                                    day_span = max(times) - min(times)
                                                    day_hours += day_span
                                                    # Format span string for activity display
                                                    s_min = f"{int(min(times)):02d}:{int((min(times)%1)*60):02d}"
                                                    e_max = f"{int(max(times)%24):02d}:{int((max(times)%1)*60):02d}"
                                                    day_activities.append(f"📍 {city} ({c['campaign_name']}) [{s_min}-{e_max}]")
                                                else:
                                                    day_hours += 12
                                                    day_activities.append(f"📍 {city} ({c['campaign_name']})")
                                except: pass
                if day_activities:
                    daily_rows.append({
                        'Data': curr,
                        'Șofer': drv_name,
                        'Ore': round(day_hours, 1),
                        'Activități': ", ".join(list(set(day_activities)))
                    })
                curr += datetime.timedelta(days=1)
        
        if daily_rows:
            df_daily = pd.DataFrame(daily_rows)
            df_daily_sorted = df_daily.sort_values(['Data', 'Șofer'], ascending=[False, True])
            
            # Pagination for Daily Breakdown
            d_items = len(df_daily_sorted)
            dp_col1, dp_col2 = st.columns([2, 1])
            d_page_size = dp_col2.selectbox(_("Rows per page"), [10, 20, 50, 100], index=0, key="d_page_size")
            d_total_pages = max(1, (d_items + d_page_size - 1) // d_page_size)
            d_page = dp_col1.number_input(_("Page") + f" (1-{d_total_pages})", min_value=1, max_value=d_total_pages, value=1, key="d_page")
            
            d_start = (d_page - 1) * d_page_size
            d_end = min(d_start + d_page_size, d_items)
            st.dataframe(df_daily_sorted.iloc[d_start:d_end], use_container_width=True)
            
            # Export Daily
            csv_d = df_daily.to_csv(index=False).encode('utf-8')
            st.download_button("📥 " + _("Download CSV Report"), csv_d, f"raport_zilnic_{start_date}_{end_date}.csv", "text/csv")
        else:
            st.info("Nicio activitate detaliată găsită.")

        # --- Export Aggregated ---
        st.divider()
        st.subheader("📥 Export Condică Completă")
        col_exp1, col_exp2 = st.columns(2)
        
        csv_full = df.to_csv(index=False).encode('utf-8')
        col_exp1.download_button("Descarcă CSV", csv_full, f"condica_{start_date}_{end_date}.csv", "text/csv")
        
        try:
            import io
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Condica')
            col_exp2.download_button("Descarcă Excel", buf.getvalue(), f"condica_{start_date}_{end_date}.xlsx", 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        except:
            col_exp2.info("Instalează `xlsxwriter` pentru export Excel.")

if __name__ == "__main__":
    main()
