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
        
        if st.button(_("Save Profile"), width="stretch"):
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
            
        if st.button(_("Save Colors"), width="stretch"):
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
        
        if st.button(_("Save Notification Settings"), width="stretch"):
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
        st.subheader("📖 " + _("Ghid de Utilizare & Documentație"))
        
        help_dashboard, help_fleet, help_campaigns, help_cities = st.tabs([
            "📊 Dashboard", "🚛 Flotă & Documente", "📋 Campanii & Rapoarte", "🏙️ Orașe & Audiență"
        ])
        
        with help_dashboard:
            st.markdown(f"""
            ### 📊 Dashboard & Overview
            În secțiunea principală a aplicației puteți vizualiza statusul general al flotei și programările campaniilor curente.
            
            **Indicatori de Bază**:
            *   **Total Vehicule**: Numărul total de mașini din sistem (inclusiv cele inactive).
            *   **Active Fleet**: Mașinile disponibile care nu sunt în mentenanță sau defecte.
            *   **Defective**: Numărul mașinilor raportate cu probleme (cu status Defect sau Mentenanță). Acestea vor fi marcate distinct în campaniile alocate.
            
            **Gantt Chart (Timeline-ul Flotei)**:
            Afișează vizual ocuparea mașinilor. Puteți filtra vizualizarea folosind:
            *   **Orizontul de timp**: Selectați perioada vizată (Luna Curentă, Următoarele 3 Luni etc.)
            *   **Status Campanii/Mașini**: Alegeți detaliile relevante pentru a planifica resursele liber disponibile.
            *   **Mod de partajare**: Se afișează fiecare perioadă per oraș. Tipurile principale sunt 'Campanie' și perioadele de 'Tranzit' între orașe.
            """)
            
        with help_fleet:
            st.markdown(f"""
            ### 🚛 Gestiunea Flotei și Resurselor Umane
            Secțiunea "Fleet" este responsabilă pentru managementul mașinilor, șoferilor și a documentelor aferente.
            
            #### 1. Vehicule & Mentenanță
            *   **Adăugare Vehicule**: Fiecare vehicul nou introdus necesită date tehnice și de registru (ex: Număr Înmatriculare). Un parametru important este **Ecrane (POC)**, care definește câte ecrane LED sunt montate pe mașină. Acesta funcționează ca un multiplicator pentru vizualizările (impresiile) estimate în rapoarte.
            *   **Istoric Status**: Statusul unui vehicul (ex: Defect, Activ) are un istoric detaliat, marcând modificările din timp. Când un vehicul intră în mentenanță, sistemul **alertează și blochează** alocarea sa pe campaniile existente ce se suprapun.
            *   **Mentenanță & Revizii**: Generații intrări în jurnal pentru schimburile de ulei, service frâne etc., setând alertele pe bază de km sau dată (ex: *Expiră la 150000 km*).
            
            #### 2. Șoferi
            *   **Asignare**: Șoferii pot fi asignați unui singur vehicul în mod activ, istoricul asignărilor păstrându-se automat.
            *   **Documente Medicale/Psihologice**: Monitorizați alertele expirării pentru controlul medical prin sistemul de date al șoferului.
            
            #### 3. Managerul de Documente & Alerte
            *   Sistemul permite încărcarea și organizarea polițelor (RCA, CASCO, ITP, Rovinietă) cu generarea codurilor de stare (Expirat/Valid/Expiră în Curând) vizibile sumarizate în notificările globale de sistem de pe Dashboard.
            """)
            
        with help_campaigns:
            st.markdown(f"""
            ### 📋 Campanii, Condica & Generare Rapoarte
            Aceasta sectiune este piesa centrala a aplicatiei, coreland audienta, masinile si performanta generand raportarile clientului.
            
            #### Moduri de Configurare
            *   **Shared Schedule**: Setarile (orelor/oraselor) se aplica concomitent tuturor masinilor alocate. Se folosește cand o intreaga flotila ruleaza aceeasi campanie in aceleasi orase.
            *   **Individual Schedule**: Ofera posibilitatea setarilor distincte. Vehiculul X pleaca spre Bacau, Vehiculul Y activeaza doar in Bucuresti, chiar daca tin de aceeasi campanie.
            
            #### Adaugarea Perioadelor de Tranzit (Condica)
            *   Pe parcursul unei campanii, perioadele in care masina doar "tranziteaza", fara expunere la public, trebuie introduse prin functia *Tranzit*. Aceste ore **sunt excluse din calculele finale OTS**.
            
            #### 📈 Raport DOOH (Financiar & Auditat)
            Acest raport special ofera metrici avansate de ROI si performanta auditata:
            - **Sincronizare Impresii**: Valorile de baza sunt acum sincronizate automat cu "Raportul de Campanie" standard pentru o consistenta totala.
            - **Metodologie Elite**: Rapoartele includ acum formule explicite bazate pe **PMUD 2021-2030**, luand in calcul **Factorul de Ocupare (1.65)**, **Densitatea Studentilor** si **Impactul Congestiei (LOS D-F)** asupra vizibilitatii.
            - **Ajustare pe Baza Datelor Auditate**: Daca sunt prezente date de teren (ore confirmate VnNox), sistemul scaleaza automat impresiile estimate pentru a reflecta performanta reala verificata.
            - **eCPK (Effective Cost Per K)**: Calculeaza costul real la 1000 de impresii folosind **Bugetul Campaniei** introdus in detalii.
            
            #### 📊 Anexa PoP (Proof of Play)
            Suplimentar Raportului DOOH, sistemul poate genera o anexă tehnică detaliată "Anexa PoP". Aceasta include:
            - **Harta GPS (Traseu Zilnic)**: Harta vizuală auto-generată cu polilinii de culori diferite reprezentând cursele zilnice ale vehiculului.
            - **Tabel Pings VnNox**: Preluare directă din log-urile VnNox cu dovada numărului de spoturi per ecran.

            #### 🔍 Gestiune Date Auditate & Modele Import
            Tab-ul dedicat permite importul datelor de teren si configurarea costurilor pentru o precizie maxima. Sistemul previne **importul duplicatelor** (același interval de date) lăsând opțiunea de suprascriere a datelor vechi.
            - **Import GPS (Model Excel/CSV)**: Generează coordonatele și construiește hărțile din Anexa PoP.
            - **Import VnNox / PoP (Model CSV)**: Validare dovadă de rulare pe ecrane.
            - **Impact Meteo**: Corectie manuala (%) pentru a reflecta conditiile atmosferice reale.
            """)
            
        with help_cities:
            st.markdown(f"""
            ### 🏙️ Orașe, Audiență & Actualizări Demografice
            Metodologia rapoartelor DOOH se bazează esențial pe informațiile stocate în această secțiune. Pentru precizie OTS (Opportunity to See), asigurați corectitudinea datelor!
            
            #### Parametri Esențiali
            *   **Modal Split (%)**: Procentajele aferente transportului (Auto / Walking / Public / Cycling). Impactul vizual se adresează grupurilor expuse direct publicității mobile.
            *   **Trafic Zilnic și Pietonal**: Se completează automat (dacă modul e Public/INS) sau Manual. Calculează audiența per locație.
            
            #### Metode de Actualizare Date
            Selectați metoda prin care platforma trage datele orașului respectiv:
            *   **Public (Surse Publice API)**: Interogări deschise (OpenStreetMap/Nominatim) pentru populație și coordonate.
            *   **INS (Statistici Naționale)**: Date oficiale de la Institutul Național de Statistică pentru precizie demografică.
            *   **BRAT (Audit Media)**: Valorile auditate oficial în România; metoda recomandată pentru rapoartele comerciale finale către agenții.
            *   **Manual**: Permite introducerea manuală a fluxului auto/pietonal (util pentru zone noi sau evenimente atipice).
            
            #### 📍 Import Date GPS & VnNox
            Sistemul permite validarea *PoP (Proof of Play)* prin import de fisiere. Modelele de fisiere (Sabloane) sunt disponibile direct in pagina de Gestiune Audit a campaniei.
            1.  **Date GPS (CSV)**: Se incarca log-urile masinilor. Sistemul calculeaza automat distanta reala (km) si valideaza prezenta in orasele targetate.
            2.  **Date VnNox (Logs)**: Se confirma rularea spoturilor pe ecrane. Se calculeaza orele de difuzare efective, eliminand timpii morti sau defectiunile tehnice.
            
            #### Evenimente Speciale (Special Events)
            Dacă la o dată precisă există un Târg, Festival (UNTOLD de ex.) etc., creați un *Eveniment*, alocându-i multiplicatori (M > 1 crește impactul OTS recunoscut). 
            """)

        st.divider()
        st.subheader("📚 " + _("Glosar Termeni și Acronime"))
        st.markdown(f"""
        **eCPK (Effective Cost Per K)**: Costul efectiv pentru 1000 de impresii (anterior denumit eCPM). Litera K („kilo”) înlocuiește M („mille”) pentru a evita confuzia cu mila engleză.

        **OTS (Opportunity To See)**: Numărul mediu de ori pe care o persoană din audiență a fost expusă la mesaj.
        
        **PMUD**: Planul de Mobilitate Urbană Durabilă - Document strategic care analizează mobilitatea urbană la nivelul orașelor din România.

        **SOV (Share of Voice)**: Procentul din timpul total de difuzare pe care îl ocupă spotul unei campanii în bucla (loop-ul) de reclame de pe ecran.

        **Reach**: Audiența netă sau acoperirea campaniei, reprezentând numărul unic de indivizi expuși mesajului proporțional cu populația activă.

        **POC (Point of Contact / Ecrane)**: Numărul de ecrane LED active montate pe un vehicul. Funcționează automat ca un multiplicator pentru impresiile generate (ex: 3 ecrane = x3 vizualizări auto/pietonale aferente rutei).
        """)

        st.divider()
        st.subheader("ℹ️ System Information")
        st.markdown(f"""
        **{_('Version')}:** 4.3 (Elite Reporting Edition)  
        **Maintainer:** Cătălin Dragomirescu  
        **Contact:** 0744929578 | catalin.dragomirescu@gmail.com
        """)
        
        st.info("Design and built for Fairway", icon="💼")

if __name__ == "__main__":
    main()
