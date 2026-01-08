import streamlit as st
import os
import utils

# Initialize environment
root_dir = utils.init_path()
from src.utils.i18n import _
utils.set_page_config("Dashboard", "📊")
utils.inject_custom_css()

# Import Managers (NOW that path is initialized)
# Import Managers (NOW that path is initialized)
from src.data import models as models_mod
from src.data import campaign_storage as cs_mod
from src.data import vehicle_manager as vm_mod
from src.data import driver_manager as dm_mod
import importlib

importlib.reload(models_mod)
importlib.reload(cs_mod)
importlib.reload(vm_mod)
importlib.reload(dm_mod)

from src.data.campaign_storage import CampaignStorage
from src.data.vehicle_manager import VehicleManager
from src.data.driver_manager import DriverManager
from src.data.db_config import init_db

# Ensure DB is initialized
try:
    init_db()
except Exception as e:
    st.error(f"❌ Database Initialization Error: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
    # Proceed anyway, but the error helps diagnosis
    pass

def main():
    st.title(_("Mobile DOOH Management"))
    
    # Debug Info for Database
    import os as _os
    from src.data.db_config import DB_PATH
    if st.sidebar.checkbox("Show Debug Info", value=False):
        st.sidebar.write(f"DB Path: `{DB_PATH}`")
        st.sidebar.write(f"DB Exists: `{_os.path.exists(DB_PATH)}`")
        if _os.path.exists(DB_PATH):
            st.sidebar.write(f"DB Size: `{_os.path.getsize(DB_PATH)}` bytes")
    st.subheader(_("Dashboard Overview"))

    # Initialize Managers
    campaign_storage = CampaignStorage()
    vehicle_manager = VehicleManager()
    driver_manager = DriverManager()

    # Fetch Stats
    total_campaigns = len(campaign_storage.get_all_campaigns())
    total_vehicles = len(vehicle_manager.get_all_vehicles())
    active_vehicles = len(vehicle_manager.get_active_vehicles())
    total_drivers = len(driver_manager.get_all_drivers())
    
    # Defective / Maintenance count
    all_v = vehicle_manager.get_all_vehicles()
    defective_count = len([v for v in all_v if v.get('status') in ['defective', 'maintenance']])

    # Layout: Stats Icons
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(_("Total Campaigns"), total_campaigns)
    with col2:
        st.metric(_("Total Vehicles"), total_vehicles)
    with col3:
        st.metric(_("Active Fleet"), f"{active_vehicles}/{total_vehicles}")
    with col4:
        st.metric(_("Defective"), defective_count, delta=-defective_count if defective_count > 0 else 0, delta_color="inverse")
    with col5:
        st.metric(_("Total Drivers"), total_drivers)

    # --- Notifications Section ---
    from src.services.notification_manager import NotificationManager
    from src.data.company_settings import CompanySettings
    
    nm = NotificationManager()
    cs = CompanySettings()
    settings = cs.get_settings()
    
    all_notifs = nm.get_all_notifications()
    
    # Filter based on preferences
    filtered_notifs = []
    for n in all_notifs:
        if n['category'] == 'Fleet' and not settings.get('show_impacts_app', True): continue
        if n['category'] == 'Documents' and not settings.get('show_expiries_app', True): continue
        if n['category'] == 'Campaigns' and not settings.get('show_gaps_app', True): continue
        filtered_notifs.append(n)
        
    if filtered_notifs:
        with st.expander(_("Notificări Sistem") + f" ({len(filtered_notifs)})", expanded=True):
            for n in filtered_notifs:
                if n['severity'] == 'error' or n['severity'] == 'critical':
                    st.error(f"**{n['type']}**: {n['message']}")
                    st.caption(n['details'])
                else:
                    st.warning(f"**{n['type']}**: {n['message']}")
                    st.caption(n['details'])

    st.divider()

    # Main Actions
    st.write("### " + _("Quick Actions"))
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.info("#### 📁 " + _("Campaigns"))
        st.write(_("Manage client campaigns and generate PDF reports."))
        if st.button(_("Manage Campaigns"), use_container_width=True):
            st.switch_page("pages/1_Campaigns.py")
        if st.button(_("Condică (Timesheet)"), use_container_width=True):
            st.switch_page("pages/1_Timesheet.py")
    with c2:
        st.success("#### 🚛 " + _("Fleet Management"))
        st.write(_("Track vehicles, drivers, and document expiry dates."))
        if st.button(_("Fleet Management"), use_container_width=True):
            st.switch_page("pages/2_Fleet.py")
    with c3:
        st.warning("#### 🏙️ " + _("Cities & Events"))
        st.write(_("Update population data and event multipliers."))
        if st.button(_("Manage Cities"), use_container_width=True):
            st.switch_page("pages/3_Cities.py")

    st.divider()
    
    # --- Campaign Schedule Gantt ---
    st.write("### " + _("Fleet Schedule Timeline"))
    import plotly.express as px
    import datetime
    import pandas as pd
    
    from src.data.company_settings import CompanySettings
    cs_mgr = CompanySettings()
    c_settings = cs_mgr.get_settings()
    custom_colors = c_settings.get('timeline_colors', {})
    
    # 1. Exhaustive Status Lists
    C_STATUS_ALL = [_("Confirmed"), _("Pending"), _("Draft"), _("Completed"), _("Cancelled")]
    V_STATUS_ALL = [_("Transit"), _("Maintenance"), _("Defective"), _("Other")] # Removed Active
    D_STATUS_ALL = [_("Vacation"), _("Medical"), _("Unpaid"), _("Free"), _("Other")] # Removed Active

    # Timeline Filters (Horizon & Statuses)
    f_col1, f_col2, f_col3 = st.columns([1.2, 1.4, 1.4])
    horizon_opt = f_col1.selectbox(_("Orizont Timp"), [_("Current Month"), _("Last Month"), _("Next 3 Months"), _("Current Year"), _("Last 3 Months"), _("Custom Range"), _("Full History")])
    
    sel_c_states = f_col2.multiselect(_("Status Campanii"), options=C_STATUS_ALL, default=C_STATUS_ALL)
    sel_v_states = f_col3.multiselect(_("Stare Mașini"), options=V_STATUS_ALL, default=V_STATUS_ALL)
    sel_d_states = f_col1.multiselect(_("Stare Șoferi"), options=D_STATUS_ALL, default=D_STATUS_ALL)

    # Resource Selection
    fr_col1, fr_col2 = st.columns(2)
    all_v = vehicle_manager.get_all_vehicles()
    v_map = {v['id']: f"{v['name']} ({v['registration']})" for v in all_v}
    v_ids_all = list(v_map.keys())
    selected_v_ids = fr_col1.multiselect(_("Vehicule"), options=v_ids_all, format_func=lambda x: v_map[x], default=v_ids_all)
    
    all_d = driver_manager.get_all_drivers()
    d_map = {d['id']: d['name'] for d in all_d}
    d_ids_all = list(d_map.keys())
    selected_d_ids = fr_col2.multiselect(_("Șoferi"), options=d_ids_all, format_func=lambda x: d_map[x], default=d_ids_all)

    today = datetime.date.today()
    start_filter, end_filter = None, None
    
    # Date Filtering logic
    if horizon_opt == _("Current Month"):
        start_filter = datetime.date(today.year, today.month, 1)
        if today.month == 12: end_filter = datetime.date(today.year + 1, 1, 1)
        else: end_filter = datetime.date(today.year, today.month + 1, 1)
        end_filter -= datetime.timedelta(days=1)
    elif horizon_opt == _("Last Month"):
        if today.month == 1:
            start_filter = datetime.date(today.year - 1, 12, 1)
            end_filter = datetime.date(today.year - 1, 12, 31)
        else:
            start_filter = datetime.date(today.year, today.month - 1, 1)
            # Find last day of last month
            next_mn = datetime.date(today.year, today.month, 1)
            end_filter = next_mn - datetime.timedelta(days=1)
    elif horizon_opt == _("Next 3 Months"):
        start_filter = today
        end_filter = today + datetime.timedelta(days=90)
    elif horizon_opt == _("Current Year"):
        start_filter = datetime.date(today.year, 1, 1)
        end_filter = datetime.date(today.year, 12, 31)
    elif horizon_opt == _("Last 3 Months"):
        start_filter = today - datetime.timedelta(days=90)
        end_filter = today
    elif horizon_opt == _("Custom Range") or horizon_opt == "Custom Range":
        c_dates = st.date_input(_("Select Range"), value=[today, today + datetime.timedelta(days=30)])
        if len(c_dates) == 2:
            start_filter, end_filter = c_dates
    
    # Collect Data
    gantt_data = []
    v_sch_raw = vehicle_manager.get_vehicle_schedules()
    
    def add_to_gantt(res_name, label, start, end, status, color_grp, hours_info=None):
        if not res_name: return
        s_date = utils.ensure_date(start)
        e_date = utils.ensure_date(end)
        if not s_date or not e_date: return

        # Global filter by date
        if start_filter and end_filter:
            if not (s_date <= end_filter and e_date >= start_filter):
                return
        
        status_cap = status.capitalize()
        if status_cap == "Active": return
        if color_grp == "Campaign" and _(status_cap) not in sel_c_states: return
        if color_grp in ["Vehicle Event", "Transit"] and _(status_cap) not in sel_v_states: return
        if color_grp == "Driver Event" and _(status_cap) not in sel_d_states: return

        default_h = "09:00-17:00" if color_grp == "Campaign" else "00:00-24:00"
        intervals = utils.get_granular_intervals(s_date, e_date, hours_info, default_h)
        
        for g_start, g_end in intervals:
            g_s_date = utils.ensure_date(g_start)
            g_e_date = utils.ensure_date(g_end)
            
            # Sub-filter the intervals by the global horizon
            if start_filter and end_filter:
                if not (g_s_date <= end_filter and g_e_date >= start_filter):
                    continue
                    
            gantt_data.append({
                "Resource": res_name,
                "Event": label,
                "Start": g_start,
                "Finish": g_end,
                "RealEnd": g_end,
                "Status": status_cap,
                "Group": color_grp
            })

    # A. Campaigns & Transit Specifics (Granular per City/Period/Driver)
    all_campaigns = campaign_storage.get_all_campaigns()
    for c in all_campaigns:
        c_status = (c.get('status') or 'confirmed').capitalize()
        c_start_glob = utils.ensure_date(c['start_date'])
        c_end_glob = utils.ensure_date(c['end_date'])
        if not c_start_glob: continue
        
        c_periods = c.get('city_periods', {})
        if not isinstance(c_periods, dict): c_periods = {}
        c_schedules = c.get('city_schedules', {})
        
        # Robust shared mode detection
        meta = c_periods.get('__meta__', {})
        if isinstance(meta, dict) and 'shared_mode' in meta:
            shared_mode = meta['shared_mode']
        else:
            # Heuristic: if any key is a known vehicle ID, it's individual mode
            shared_mode = True
            for k in c_periods.keys():
                if k == '__meta__': continue
                if k in v_ids_all: # v_ids_all defined above
                    shared_mode = False
                    break
        
        # Determine vehicles and drivers in this campaign
        v_list = []
        if c.get('vehicle_id'):
            v_list.append({'id': c['vehicle_id'], 'name': c.get('vehicle_name', 'N/A'), 'driver': c.get('driver_name', 'N/A')})
        for av in c.get('additional_vehicles', []):
            v_list.append({'id': av.get('vehicle_id'), 'name': av.get('vehicle_name', 'N/A'), 'driver': av.get('driver_name', 'N/A')})

        # Logic to add granular periods
        added_any_granular = False
        
        if shared_mode:
            # All vehicles share the same city periods
            for city, periods in c_periods.items():
                if city == '__meta__': continue
                if not isinstance(periods, list): periods = [periods]
                
                # Try to find representative hours for this city
                city_hours = ""
                city_sched = c_schedules.get(city, {})
                if city_sched:
                    # Look for first non-empty hours
                    for day_data in city_sched.values():
                        if day_data.get('hours'):
                            city_hours = f" [🕒 {day_data['hours']}]"
                            break

                for p in periods:
                    ps = utils.ensure_date(p.get('start'))
                    pe = utils.ensure_date(p.get('end'))
                    if not ps or not pe: continue
                    
                    for v_info in v_list:
                        v_name_clean = v_info['name']
                        d_name_clean = v_info['driver']
                        
                        # Labels
                        label_v = f"📍 {city} | {c['campaign_name']} (👤 {d_name_clean}){city_hours}"
                        label_d = f"📍 {city} | {c['campaign_name']} (🚛 {v_name_clean}){city_hours}"

                        # Add to Vehicle row
                        if v_info['id'] in selected_v_ids:
                            add_to_gantt(v_map.get(v_info['id']), label_v, ps, pe, c_status, "Campaign", hours_info=city_sched)
                            added_any_granular = True
                        # Add to Driver row
                        for d_id in selected_d_ids:
                            if d_map.get(d_id) == d_name_clean:
                                add_to_gantt(d_name_clean, label_d, ps, pe, c_status, "Campaign", hours_info=city_sched)
                                added_any_granular = True
                added_any_granular = True
        else:
            # Each vehicle has its own cities
            for v_id, cities_data in c_periods.items():
                if v_id == '__meta__': continue
                if v_id not in selected_v_ids: continue
                # Find details for this vehicle
                v_info = next((v for v in v_list if v['id'] == v_id), {'driver': 'N/A'})
                
                if isinstance(cities_data, dict):
                    for city, periods in cities_data.items():
                        if not isinstance(periods, list): periods = [periods]
                        
                        # Hours for this vehicle/city
                        city_hours = ""
                        v_city_sched = c_schedules.get(v_id, {}).get(city, {})
                        if v_city_sched:
                            for day_data in v_city_sched.values():
                                if day_data.get('hours'):
                                    city_hours = f" [🕒 {day_data['hours']}]"
                                    break

                        for p in periods:
                            ps = utils.ensure_date(p.get('start'))
                            pe = utils.ensure_date(p.get('end'))
                            if not ps or not pe: continue
                            v_name_clean = v_info['name']
                            d_name_clean = v_info['driver']
                            
                            label_v = f"📍 {city} | {c['campaign_name']} (👤 {d_name_clean}){city_hours}"
                            label_d = f"📍 {city} | {c['campaign_name']} (🚛 {v_name_clean}){city_hours}"

                            # Add to Vehicle
                            if v_id in selected_v_ids:
                                add_to_gantt(v_map.get(v_id), label_v, ps, pe, c_status, "Campaign", hours_info=v_city_sched)
                                added_any_granular = True
                            # Add to Driver
                            for drv_id in selected_d_ids:
                                if d_map.get(drv_id) == d_name_clean:
                                    add_to_gantt(d_name_clean, label_d, ps, pe, c_status, "Campaign", hours_info=v_city_sched)
                                    added_any_granular = True
                added_any_granular = True

        # Fallback to global if no granular periods
        if not added_any_granular:
            for v_info in v_list:
                label_v = f"🚩 {c['campaign_name']} (Global) | 👤 {v_info['driver']}"
                label_d = f"🚩 {c['campaign_name']} (Global) | 🚛 {v_info['name']}"
                # Add to Vehicle
                if v_info['id'] in selected_v_ids:
                    add_to_gantt(v_map.get(v_info['id']), label_v, c_start_glob, c_end_glob, c_status, "Campaign")
                # Add to Driver
                for d_id in selected_d_ids:
                    if d_map.get(d_id) == v_info['driver']:
                        add_to_gantt(v_info['driver'], label_d, c_start_glob, c_end_glob, c_status, "Campaign")

        # Transit periods WITHIN campaigns - Isolated from global
        for tp in c.get('transit_periods', []):
            tp_vid = tp.get('vehicle_id')
            if tp_vid in selected_v_ids:
                ts = utils.ensure_date(tp.get('start'))
                te = utils.ensure_date(tp.get('end'))
                if not ts or not te: continue
                
                # Find driver for this vehicle in this campaign
                drv_name = "N/A"
                for v_info in v_list:
                    if v_info['id'] == tp_vid:
                        drv_name = v_info['driver']
                        break
                        
                t_hours = f" [🕒 {tp['hours']}]" if tp.get('hours') else ""
                label_v = f"🚚 Tranzit: {tp.get('origin')} ➡ {tp.get('destination')} ({c['campaign_name']}) (👤 {drv_name}){t_hours}"
                label_d = f"🚚 Tranzit: {tp.get('origin')} ➡ {tp.get('destination')} ({c['campaign_name']}) (🚛 {v_map.get(tp_vid)}){t_hours}"
                
                # Add to Vehicle
                add_to_gantt(v_map.get(tp_vid), label_v, ts, te, "Transit", "Transit", hours_info=tp.get('hours'))
                # Add to Driver if selected
                for d_id in selected_d_ids:
                    if d_map.get(d_id) == drv_name:
                        add_to_gantt(drv_name, label_d, ts, te, "Transit", "Transit", hours_info=tp.get('hours'))

    # B. Vehicle Schedules (Global - Non-Campaign)
    for s in v_sch_raw:
        vid = s['vehicle_id']
        if vid in selected_v_ids:
            s_start = utils.ensure_date(s.get('start'))
            s_end = utils.ensure_date(s.get('end'))
            if not s_start or not s_end: continue
            
            s_type_cap = s['type'].capitalize()
            v_name = v_map.get(vid)
            
            # Find current driver for this vehicle for the timeline
            drv_info = next((v for v in all_v if v['id'] == vid), {})
            d_name = drv_info.get('driver_name')
            
            label_v = f"🚩 {s_type_cap} (👤 {d_name if d_name else 'N/A'})"
            if s.get('origin') and s.get('destination'):
                label_v = f"🚚 Tranzit: {s['origin']} ➡ {s['destination']} (👤 {d_name if d_name else 'N/A'})"
            
            label_d = f"🚩 {s_type_cap} (🚛 {v_name})"
            if s.get('origin') and s.get('destination'):
                label_d = f"🚚 Tranzit: {s['origin']} ➡ {s['destination']} (🚛 {v_name})"

            # Add to Vehicle
            add_to_gantt(v_name, label_v, s_start, s_end, s_type_cap, "Vehicle Event")
            # Add to Driver if they exist and are selected
            if d_name:
                for d_id in selected_d_ids:
                    if d_map.get(d_id) == d_name:
                        add_to_gantt(d_name, label_d, s_start, s_end, s_type_cap, "Vehicle Event")

    # C. Driver Schedules (Global)
    for d_id in selected_d_ids:
        d_schedules = driver_manager.get_driver_schedules(d_id)
        for ds in d_schedules:
            ds_start = utils.ensure_date(ds.get('start_date'))
            ds_end = utils.ensure_date(ds.get('end_date'))
            if not ds_start or not ds_end: continue
            add_to_gantt(d_map.get(d_id), ds['event_type'].capitalize(), ds_start, ds_end, ds['event_type'].capitalize(), "Driver Event")

    # D. Baseline "Active" bars
    if start_filter and end_filter:
        seen_resources = set(d['Resource'] for d in gantt_data)
        for v_id in selected_v_ids:
            name = v_map.get(v_id)
            if name not in seen_resources:
                add_to_gantt(name, _("Disponibil / Activ"), start_filter, end_filter, "Active", "Baseline")
        for d_id in selected_d_ids:
            name = d_map.get(d_id)
            if name not in seen_resources:
                add_to_gantt(name, _("Disponibil / Activ"), start_filter, end_filter, "Active", "Baseline")

    if gantt_data:
        df_gantt = pd.DataFrame(gantt_data)
        df_gantt['Start'] = pd.to_datetime(df_gantt['Start'])
        df_gantt['Finish'] = pd.to_datetime(df_gantt['Finish'])
        df_gantt['RealEnd'] = pd.to_datetime(df_gantt['RealEnd'])
        
        # Color palette logic
        full_color_map = {
            "Confirmed": "#FFD700", "Pending": "#ffc107", "Draft": "#6c757d", "Completed": "#007bff", "Cancelled": "#dc3545",
            "Maintenance": "#dc3545", "Defective": "#f82c2c", "Transit": "#28a745", "Other": "#adb5bd",
            "Vacation": "#e83e8c", "Medical": "#6f42c1", "Unpaid": "#343a40"
        }
        # Override with custom colors from settings
        for key, val in custom_colors.items():
            full_color_map[key] = val
        
        fig = px.timeline(
            df_gantt, 
            x_start="Start", 
            x_end="Finish", 
            y="Resource", 
            color="Status", 
            hover_name="Event",
            hover_data={
                "Start": "|%d.%m.%Y %H:%M",
                "RealEnd": "|%d.%m.%Y %H:%M",
                "Finish": False,
                "Status": True
            },
            labels={"RealEnd": _("Sfarsit")},
            color_discrete_map=full_color_map,
            template="plotly_white",
            category_orders={"Resource": sorted(df_gantt["Resource"].unique())}
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(
            height=300 + (len(df_gantt["Resource"].unique()) * 35),
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        if horizon_opt in ["Full History", "Current Year", "Custom Range"]:
            fig.update_xaxes(rangeslider_visible=True)
            
        # FORCE X-AXIS RANGE
        if start_filter and end_filter:
            fig.update_xaxes(range=[start_filter, end_filter])
            
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(_("No active schedules found for the selected filters."))

    st.divider()

    # Recent Campaigns Minimal Table
    st.write("### 📋 " + _("Recent Campaigns"))
    recent_campaigns = campaign_storage.get_all_campaigns()[:5]
    if recent_campaigns:
        # Prepare table data
        table_data = []
        for c in recent_campaigns:
            table_data.append({
                _("Campaign Name"): c['campaign_name'],
                _("Client"): c['client_name'],
                _("Period"): f"{c['start_date']} to {c['end_date']}",
                _("Status"): c.get('status') or _("Draft")
            })
        st.table(table_data)
    else:
        st.info(_("No campaigns found yet."))

if __name__ == "__main__":
    main()
