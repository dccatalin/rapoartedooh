import streamlit as st
import utils
import pandas as pd
import json
import datetime
import importlib
import sys
from src.utils.i18n import _

# Initialize
root_dir = utils.init_path()
utils.set_page_config("Cities & Events", "🏙️")
utils.inject_custom_css()

# Imports
from src.data.city_data_manager import CityDataManager
from src.data.company_settings import CompanySettings

city_manager = CityDataManager()
cs = CompanySettings()

def main():
    st.title(_("City & Event Management"))
    
    cities = sorted(city_manager.get_all_cities())
    
    # --- Pagination State ---
    if 'city_page' not in st.session_state:
        st.session_state.city_page = 0
    if 'cities_per_page' not in st.session_state:
        st.session_state.cities_per_page = 15
        
    col_list, col_edit = st.columns([1, 3])
    
    with col_list:
        st.write("### " + _("Cities"))
        
        # Pagination Controls
        total_cities = len(cities)
        page_size = st.selectbox(_("Show:"), [10, 15, 20, 50, 100], index=[10, 15, 20, 50, 100].index(st.session_state.cities_per_page))
        if page_size != st.session_state.cities_per_page:
            st.session_state.cities_per_page = page_size
            st.session_state.city_page = 0
            st.rerun()
            
        total_pages = (total_cities - 1) // page_size + 1 if total_cities > 0 else 1
        
        start_idx = st.session_state.city_page * page_size
        end_idx = min(start_idx + page_size, total_cities)
        paged_cities = cities[start_idx:end_idx]
        
        selected_city = st.radio(_("Select a city to edit:"), options=paged_cities, label_visibility="collapsed")
        
        # Navigation
        c_prev, c_page, c_next = st.columns([1, 2, 1])
        if c_prev.button("⬅️", disabled=st.session_state.city_page == 0):
            st.session_state.city_page -= 1
            st.rerun()
        
        c_page.write(_("Page") + f" **{st.session_state.city_page + 1}** " + _("of") + f" {total_pages}")
        
        if c_next.button("➡️", disabled=st.session_state.city_page >= total_pages - 1):
            st.session_state.city_page += 1
            st.rerun()

        st.divider()
        if st.toggle("➕ " + _("Add New City")):
            with st.form("new_city_form"):
                new_city_name = st.text_input(_("City Name"))
                new_pop = st.number_input(_("Population"), min_value=0, value=10000)
                if st.form_submit_button(_("Initialize City")):
                    if new_city_name:
                        # Use extrapolation to get base data
                        base_data = city_manager.extrapolate_city_data(new_city_name, new_pop)
                        
                        # Apply global default update mode
                        settings = cs.get_settings()
                        default_mode = settings.get('default_city_update_mode', 'public')
                        base_data['update_preference'] = default_mode
                        
                        city_manager.add_city(new_city_name, base_data)
                        st.success(_("City") + f" {new_city_name} " + _("initialized with") + f" {default_mode} " + _("update mode!"))
                        st.rerun()
                    else:
                        st.error(_("City name is required."))

    with col_edit:
        if selected_city:
            profile = city_manager.get_city_profile(selected_city)
            if profile:
                st.header(_("Editing") + f": {selected_city}")
                
                # Update Preference
                prefs = ["public", "ins", "brat", "manual"]
                current_pref = city_manager.get_update_preference(selected_city)
                
                new_pref = st.selectbox(
                    _("Data Update Mode"), 
                    options=prefs, 
                    index=prefs.index(current_pref) if current_pref in prefs else 0,
                    help=_("Public: Automatic from web sources. INS: Statistics Institute. BRAT: Audited data. Manual: No automatic updates.")
                )
                
                if new_pref != current_pref:
                    if city_manager.set_update_preference(selected_city, new_pref):
                        st.success(_("Data update mode changed to") + f" {new_pref}")
                
                # Full Demographics & Modal Split Form
                with st.form("city_full_edit"):
                    st.subheader("📊 " + _("Demographics"))
                    d_col1, d_col2 = st.columns(2)
                    pop = d_col1.number_input(_("Population"), value=int(profile.get('population', 0)), step=1000)
                    county = d_col2.text_input(_("County"), value=profile.get('county', ""))
                    
                    active_pop = d_col1.slider(_("Active Population %"), 0, 100, value=int(profile.get('active_population_pct', 58)))
                    commute = d_col2.number_input(_("Avg Commute (km)"), value=float(profile.get('avg_commute_distance_km', 8.0)), step=0.5)
                    
                    traffic = d_col1.number_input(_("Daily Traffic (vehicles)"), value=int(profile.get('daily_traffic_total', 0)), step=100)
                    pedes = d_col2.number_input(_("Daily Pedestrians"), value=int(profile.get('daily_pedestrian_total', 0)), step=100)
                    
                    st.divider()
                    st.subheader("🚇 Modal Split (%)")
                    ms = profile.get('modal_split', {})
                    
                    m_col1, m_col2 = st.columns(2)
                    m_auto = m_col1.number_input("Auto %", 0, 100, value=int(ms.get('auto', 35)))
                    m_walk = m_col2.number_input("Walking %", 0, 100, value=int(ms.get('walking', 27)))
                    m_pub = m_col1.number_input("Public Transport %", 0, 100, value=int(ms.get('public_transport', 34)))
                    m_cyc = m_col2.number_input("Cycling %", 0, 100, value=int(ms.get('cycling', 4)))
                    
                    # Live Preview Chart
                    preview_data = pd.DataFrame({
                        _("Transport"): [_("Auto"), _("Walking"), _("Public"), _("Cycling")],
                        "Percentage": [m_auto, m_walk, m_pub, m_cyc]
                    })
                    st.bar_chart(preview_data.set_index(_("Transport")))
                    
                    # Optional: Add a check for 100% total
                    total_ms = m_auto + m_walk + m_pub + m_cyc
                    if total_ms != 100:
                        st.warning(_("Modal split total is") + f" {total_ms}%. " + _("It should ideally be 100%."))
 
                    if st.form_submit_button("💾 " + _("Save All City Data"), width="stretch"):
                        # Prepare updated profile
                        updated_profile = profile.copy()
                        updated_profile.update({
                            'population': pop,
                            'county': county,
                            'active_population_pct': active_pop,
                            'avg_commute_distance_km': commute,
                            'daily_traffic_total': traffic,
                            'daily_pedestrian_total': pedes,
                            'modal_split': {
                                'auto': m_auto,
                                'walking': m_walk,
                                'public_transport': m_pub,
                                'cycling': m_cyc
                            },
                            'source': 'Manual Update' if new_pref == 'manual' else profile.get('source', 'Manual Edit')
                        })
                        city_manager.add_city(selected_city, updated_profile)
                        st.success(_("Updated data for") + f" {selected_city} " + _("saved successfully!"))
                        st.rerun()
                
                # Special Events
                st.divider()
                st.subheader("📅 " + _("Special Events"))
                events = city_manager.special_events.get(selected_city, {})
                if events:
                    for date, edata in sorted(events.items()):
                        e_cols = st.columns([2, 3, 1, 1, 1])
                        e_cols[0].write(date)
                        e_cols[1].write(edata.get('name', ""))
                        e_cols[2].write(f"T:{edata.get('traffic_multiplier', 1.0)}")
                        e_cols[3].write(f"P:{edata.get('pedestrian_multiplier', 1.0)}")
                        
                        if e_cols[4].button("🗑️", key=f"del_ev_{selected_city}_{date}"):
                            del city_manager.special_events[selected_city][date]
                            city_manager._save_special_events() # We need to ensure this exists or use manual save
                            st.toast(_("Event") + f" {date} " + _("deleted!"))
                            st.rerun()
                else:
                    st.info("No special events defined for this city.")
                
                # Add Event Form
                with st.expander("➕ " + _("Add Special Event")):
                    with st.form("add_event_form"):
                        ev_name = st.text_input(_("Event Name"))
                        ev_date = st.date_input(_("Date"), value=datetime.date.today())
                        ev_t_mult = st.number_input(_("Traffic Multiplier"), value=1.0, step=0.1)
                        ev_p_mult = st.number_input(_("Pedestrian Multiplier"), value=1.0, step=0.1)
                        
                        if st.form_submit_button(_("Add Event")):
                            if ev_name:
                                if selected_city not in city_manager.special_events:
                                    city_manager.special_events[selected_city] = {}
                                
                                city_manager.special_events[selected_city][str(ev_date)] = {
                                    "name": ev_name,
                                    "start_date": str(ev_date),
                                    "end_date": str(ev_date),
                                    "traffic_multiplier": ev_t_mult,
                                    "pedestrian_multiplier": ev_p_mult
                                }
                                city_manager._save_special_events()
                                
                                st.success(f"Event added for {ev_date}!")
                                st.rerun()
                
                # Actions
                col_act2, col_act3 = st.columns(2)
                
                if col_act2.button("🔄 " + _("Refresh from Source"), help=_("Fetch latest data based on update mode"), width="stretch"):
                    with st.spinner(_("Refreshing") + f" {selected_city}..."):
                        # If mode is manual, we force it since user clicked the button
                        res = city_manager.refresh_city_data(selected_city, force=True)
                        if res['success']:
                            st.success(_("Data updated from") + f" {res.get('source', 'API')}!")
                            st.rerun()
                        else:
                            st.error(_("Failed:") + f" {res.get('message')}")
                            
                if col_act3.button("🗑️ " + _("Delete City"), type="secondary", width="stretch"):
                    if selected_city in city_manager.profiles:
                        del city_manager.profiles[selected_city]
                        city_manager._save_profiles()
                        st.toast(_("City") + f" {selected_city} " + _("deleted!"))
                        st.rerun()

if __name__ == "__main__":
    main()
