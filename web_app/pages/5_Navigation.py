import streamlit as st
import utils
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
import datetime
import json
import os
import socket

# Imports
from src.utils.i18n import _

# Initialize
root_dir = utils.init_path()
utils.set_page_config(_("DOOH Navigation"), "🚀")
utils.inject_custom_css()

# Storage Imports
from src.data.campaign_storage import CampaignStorage
from src.data.campaign_route_manager import CampaignRouteManager
def main():
    storage = CampaignStorage()
    route_manager = CampaignRouteManager()
    
    st.title("🚀 " + _("Driver Navigation"))
    st.info(_("Activez GPS-ul pe telefon pentru a urmări traseul în timp real."))
    
    # 1. Geolocation Component
    location = streamlit_geolocation()
    curr_lat, curr_lon = None, None
    
    if location and location.get('latitude'):
        curr_lat = location['latitude']
        curr_lon = location['longitude']
        st.success(f"📡 " + _("GPS Semnal: OK") + f" ({curr_lat:.5f}, {curr_lon:.5f})")
    else:
        st.warning(_("Așteptare semnal GPS..."))
        with st.expander("ℹ️ " + _("Probleme cu permisiunea de locație?")):
            # Get local IP for instructions
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except:
                local_ip = "localhost"

            st.markdown(f"""
            Browserele moderne (Chrome, Safari, Edge) blochează accesul la locație pe conexiuni **necriptate (HTTP)**. 
            Dacă accesezi aplicația prin IP local (ex: `http://192.168...`), trebuie să permiți manual accesul:
            
            **Pentru Chrome/Edge:**
            1. Deschide o fereastră nouă și scrie: `chrome://flags/#unsafely-treat-insecure-origin-as-secure`
            2. Adaugă adresa actuală a aplicației în listă: `http://{local_ip}:8501`
            3. Schimbă setarea în **Enabled** și apasă **Relaunch**.
            
            **Pentru iPhone/Safari:**
            - Safari necesită obligatoriu HTTPS sau `localhost`. Pentru acces de pe telefon în rețea locală, recomandăm folosirea Chrome cu setările de mai sus.
            """)
            if st.button(_("Am înțeles, reîncearcă")):
                st.rerun()
    
    # 2. Campaign & Route Selection
    campaigns = storage.get_all_campaigns()
    active_campaigns = [c for c in campaigns if c.get('status', 'Active') != 'Completed']
    
    col_sel1, col_sel2 = st.columns(2)
    
    if not active_campaigns:
        st.info(_("Nu există campanii active momentan."))
        return
        
    selected_camp_name = col_sel1.selectbox(_("Selectează Campania"), [c['campaign_name'] for c in active_campaigns])
    selected_camp = next(c for c in active_campaigns if c['campaign_name'] == selected_camp_name)
    
    # Fetch detailed campaign to get routes
    comp_data = storage.get_campaign(selected_camp['id'])
    routes = comp_data.get('routes', [])
    
    if not routes:
        st.error(_("Această campanie nu are trasee definite."))
        return
        
    selected_route_name = col_sel2.selectbox(_("Selectează Traseul"), [r['name'] for r in routes])
    selected_route = next(r for r in routes if r['name'] == selected_route_name)
    
    # 3. Dynamic Map
    st.markdown("---")
    
    # Determine center
    m_lat, m_lon = 44.4268, 26.1025
    if curr_lat:
        m_lat, m_lon = curr_lat, curr_lon
    elif selected_route.get('geojson_data'):
        # Center on first point of route
        geom = selected_route['geojson_data'].get('geometry', {})
        coords = geom.get('coordinates', [])
        if coords:
            if geom.get('type') == 'Point':
                m_lat, m_lon = coords[1], coords[0]
            elif geom.get('type') == 'LineString':
                m_lat, m_lon = coords[0][1], coords[0][0]
                
    m = folium.Map(location=[m_lat, m_lon], zoom_start=15)
    
    # Add Route
    if selected_route.get('geojson_data'):
        folium.GeoJson(
            selected_route['geojson_data'],
            name=selected_route['name'],
            style_function=lambda x: {'color': 'red', 'weight': 6, 'opacity': 0.8}
        ).add_to(m)
    
    # Add Driver Location Marker
    if curr_lat:
        folium.Marker(
            [curr_lat, curr_lon],
            popup=_("Poziția Ta"),
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(m)
        
        # Add a circle for accuracy/tracking feel
        folium.Circle(
            radius=20,
            location=[curr_lat, curr_lon],
            color='blue',
            fill=True,
            fill_opacity=0.2
        ).add_to(m)

    # Use st_folium but with dynamic updates
    # Note: st_folium might rerun when map is moved, but we want it for mobile
    st_folium(m, width="100%", height=500, key=f"nav_map_{selected_route['id']}")
    
    # 4. Route Instructions / Stats
    st.subheader(_("Detalii Traseu"))
    c1, c2, c3 = st.columns(3)
    c1.metric(_("Traseu"), selected_route['name'])
    c2.metric(_("Program"), f"{selected_route.get('time_start', '08:00')} - {selected_route.get('time_end', '20:00')}")
    
    v_id = selected_route.get('vehicle_id')
    from src.data.vehicle_manager import VehicleManager
    vm = VehicleManager()
    v_info = vm.get_vehicle(v_id) if v_id else None
    c3.metric(_("Vehicul"), v_info.get('license_plate', _("Orice")) if v_info else _("Orice"))

if __name__ == "__main__":
    main()
