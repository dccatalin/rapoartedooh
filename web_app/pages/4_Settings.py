import streamlit as st
import utils
import os
import importlib
import sys
from src.utils.i18n import _

# Initialize
root_dir = utils.init_path()
utils.set_page_config("Settings & Help", "⚙️")
utils.inject_custom_css()

# Imports
import src.data.company_settings as company_settings_mod
importlib.reload(company_settings_mod)
from src.data.company_settings import CompanySettings

from src.data.city_data_manager import CityDataManager

cs = CompanySettings()
city_manager = CityDataManager()

def main():
    st.title("⚙️ " + _("Settings & Help"))
    
    cs = CompanySettings()
    settings = cs.get_settings()
    
    tab_profile, tab_visuals, tab_notifs, tab_help = st.tabs([
        _("Company Profile"), 
        _("Timeline Appearance"), 
        _("Notifications & Email"), 
        _("Help & Documentation")
    ])
    with tab_profile:
        st.subheader("🏢 " + _("Company Profile"))
        
        c1, c2 = st.columns([1, 2])
        logo_path = settings.get('logo_path', '')
        if logo_path and os.path.exists(logo_path):
            c1.image(logo_path, width=150)
        
        new_logo = c1.file_uploader(_("Upload Logo"), type=['png', 'jpg', 'jpeg'])
        
        comp_name = c2.text_input(_("Company Name"), value=settings.get('name', '')) # Changed 'company_name' to 'name' to match original
        comp_addr = c2.text_area(_("Address"), value=settings.get('address', '')) # Changed 'company_address' to 'address' to match original
        reg = st.text_input(_("Registration Number (CUI/CIF)"), value=settings.get('registration_number', "")) # Added from original
        
        st.divider()
        st.subheader("⚙️ " + _("General Settings"))
        
        # City Update Mode
        city_modes = ["public", "ins", "brat", "manual"] # Changed 'update_modes' to 'city_modes' to match original
        current_mode = settings.get('default_city_update_mode', 'public') # Added from original
        default_upd = st.selectbox( # Changed 'default_upd' to 'default_mode' to match original
            _("Global Default Update Mode"), # Changed label to match original
            options=city_modes,
            index=city_modes.index(current_mode) if current_mode in city_modes else 0,
            help=_("Sets the default update mode for new cities and allows bulk updates.") # Added from original
        )
        
        apply_to_all = st.checkbox(_("Apply this mode to ALL existing cities on save")) # Added from original

        # API Keys & Paths (from original tab1)
        st.divider()
        st.subheader("🔑 " + _("API Keys & Paths"))
        g_key = st.text_input(_("Google Maps API Key"), value=settings.get('google_maps_api_key', ""), type="password")
        output_p = st.text_input(_("Reports Output Directory"), value=settings.get('reports_output_path', "")) # Changed 'reports_path' to 'reports_output_path' to match original
        
        # Developer Options (from original tab1)
        st.divider()
        st.subheader("🛠️ " + _("Developer Options"))
        col_dev1, col_dev2 = st.columns(2)
        debug_mode = col_dev1.checkbox(_("Enable Debug Mode (Global)"), value=settings.get('debug_mode', False))
        enable_spots = col_dev2.checkbox(_("Enable Spot Uploads (Global)"), value=settings.get('enable_spot_uploads', True))

        # Theme (moved from original tab2)
        st.divider()
        st.subheader("🌓 " + _("Application Theme"))
        theme_options = ["Light", "Dark", "Ocean"]
        current_theme = settings.get('theme', 'Light')
        selected_theme = st.selectbox(_("Select Theme"), options=theme_options, index=theme_options.index(current_theme) if current_theme in theme_options else 0)
        
        if st.button(_("Save Profile"), use_container_width=True):
            save_data = {
                'name': comp_name, 
                'address': comp_addr, 
                'registration_number': reg,
                'google_maps_api_key': g_key,
                'reports_output_path': output_p,
                'default_city_update_mode': default_upd, # Changed to default_upd
                'debug_mode': debug_mode,
                'enable_spot_uploads': enable_spots,
                'theme': selected_theme
            }
            
            # Handle logo upload
            if new_logo:
                logo_dir = os.path.join(root_dir, "assets", "logo")
                os.makedirs(logo_dir, exist_ok=True)
                logo_filename = "company_logo" + os.path.splitext(new_logo.name)[1]
                logo_save_path = os.path.join(logo_dir, logo_filename)
                with open(logo_save_path, "wb") as f:
                    f.write(new_logo.getbuffer())
                save_data['logo_path'] = logo_save_path
            else:
                save_data['logo_path'] = settings.get('logo_path', '') # Keep existing logo if no new one uploaded

            res = cs.save_settings(**save_data)
            if res:
                if apply_to_all:
                    count = 0
                    for city in city_manager.get_all_cities():
                        if city_manager.set_update_preference(city, default_upd): # Changed to default_upd
                            count += 1
                    st.success(_(f"Settings saved and applied to {count} cities!"))
                else:
                    st.success(_("Profile saved!"))
                st.rerun()
            else:
                st.error(_("Failed to save settings."))

    with tab_visuals:
        st.subheader("🎨 " + _("Timeline Appearance"))
        st.info(_("Customize status colors on the timeline."))
        
        saved_colors = settings.get('timeline_colors', {})
        default_colors = {
            "Active": "#e9ecef",
            "Confirmed": "#FFD700",
            "Pending": "#ffc107",
            "Draft": "#6c757d",
            "Completed": "#007bff",
            "Cancelled": "#dc3545",
            "Maintenance": "#dc3545",
            "Defective": "#f82c2c",
            "Transit": "#28a745",
            "Other": "#adb5bd",
            "Vacation": "#e83e8c",
            "Medical": "#6f42c1",
            "Unpaid": "#343a40",
            "Free": "#20c997"
        }
        
        new_colors = {}
        # Campaign Statuses
        st.write("### " + _("Campaign Colors"))
        c1, c2, c3 = st.columns(3)
        for i, status in enumerate(["Confirmed", "Pending", "Draft", "Completed", "Cancelled"]):
            col = [c1, c2, c3][i % 3]
            new_colors[status] = col.color_picker(_(status), value=saved_colors.get(status, default_colors.get(status, "#cccccc")))
            
        # Vehicle Statuses
        st.write("### " + _("Vehicle & Driver Colors"))
        v1, v2, v3 = st.columns(3)
        for i, status in enumerate(["Maintenance", "Defective", "Transit", "Other", "Vacation", "Medical", "Unpaid", "Free"]):
            col = [v1, v2, v3][i % 3]
            new_colors[status] = col.color_picker(_(status), value=saved_colors.get(status, default_colors.get(status, "#cccccc")))
            
        if st.button(_("Save Colors"), use_container_width=True):
            if cs.save_settings(timeline_colors=new_colors):
                st.success(_("Colors saved!"))
                st.rerun()

    with tab_notifs:
        st.subheader("🔔 " + _("Notifications & Email"))
        
        st.write("### " + _("SMTP Configuration"))
        smtp_host = st.text_input(_("SMTP Host"), value=settings.get('smtp_host', ''))
        smtp_port = st.number_input(_("SMTP Port"), value=int(settings.get('smtp_port', 587)))
        smtp_user = st.text_input(_("SMTP User"), value=settings.get('smtp_user', ''))
        smtp_pass = st.text_input(_("SMTP Password"), value=settings.get('smtp_password', ''), type='password')
        smtp_sender = st.text_input(_("SMTP Sender Email"), value=settings.get('smtp_sender', ''))
        smtp_tls = st.checkbox(_("Use TLS"), value=settings.get('use_tls', True))
        
        st.divider()
        st.write("### " + _("Notification Preferences"))
        recipient = st.text_input(_("Recipient Email"), value=settings.get('recipient_email', ''))
        show_app = st.checkbox(_("Show Notifications in App"), value=settings.get('show_notifs_app', True))
        send_email = st.checkbox(_("Send Email Notifications"), value=settings.get('send_notifs_email', False))
        
        if st.button(_("Save Notification Settings"), use_container_width=True):
            notif_data = {
                'smtp_host': smtp_host,
                'smtp_port': smtp_port,
                'smtp_user': smtp_user,
                'smtp_password': smtp_pass,
                'smtp_sender': smtp_sender,
                'use_tls': smtp_tls,
                'recipient_email': recipient,
                'show_notifs_app': show_app,
                'send_notifs_email': send_email
            }
            if cs.save_settings(**notif_data):
                st.success(_("Notification settings saved!"))
                st.rerun()

    with tab_help:
        st.subheader("📖 " + _("User Guide"))
        st.markdown(_("Public: Automatic from web sources. INS: Statistics Institute. BRAT: Audited data. Manual: No automatic updates."))
        
        st.markdown(f"""
        ### {_('Documentation')}
        
        #### {_('Steps to generate a report')}:
        1. **{_('Configurați Flota')}**: {_("Add new vehicles and drivers in 'Fleet'")}
        2. **{_('Verificați Orașele')}**: {_("Ensure demographic data is updated in 'Cities'")}
        3. **{_('Creați Campania')}**: {_("Enter client details, period, and assigned vehicles.")}
        4. **{_('Descărcați PDF')}**: {_("Generate report and download it locally.")}
        """)
        
        st.divider()
        st.subheader("ℹ️ " + _("System Information"))
        st.markdown(f"""
        **{_('Version')}:** 3.5 (i18n Stabilized)  
        **Maintainer:** Cătălin Dragomirescu  
        **Contact:** 0744929578 | catalin.dragomirescu@gmail.com
        """)
        
        st.info("Design and built for Fairway")

if __name__ == "__main__":
    main()
