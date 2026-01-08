import os
import sys
import streamlit as st
import datetime
from src.utils.i18n import _

def init_path():
    """Add project root to sys.path to allow imports from src/"""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root_dir not in sys.path:
        sys.path.append(root_dir)
    return root_dir

def set_page_config(title="Rapoarte DOOH", icon="📊"):
    """Standard page configuration for Streamlit"""
    st.set_page_config(
        page_title=_(title),
        page_icon=icon,
        layout="wide"
    )
    
    # Language Selector in Sidebar
    with st.sidebar:
        st.write("---")
        st.write(f"🌐 { _('Language') }")
        
        current_lang = st.session_state.get('language', 'ro')
        lang_options = {'ro': '🇷🇴 Română', 'en': '🇺🇸 English'}
        
        # Determine index
        idx = 0 if current_lang == 'ro' else 1
        
        new_lang_name = st.selectbox(
            _('Select Language'),
            options=list(lang_options.values()),
            index=idx,
            label_visibility="collapsed"
        )
        
        # Map back to code
        new_lang = 'ro' if new_lang_name == '🇷🇴 Română' else 'en'
        
        if new_lang != current_lang:
            st.session_state.language = new_lang
            # Save to CompanySettings for persistence
            from src.data.company_settings import CompanySettings
            CompanySettings().save_settings(language=new_lang)
            st.rerun()

def inject_custom_css():
    """Global CSS tweaks for a premium look with theme support"""
    from src.data.company_settings import CompanySettings
    settings = CompanySettings().get_settings()
    theme = settings.get('theme', 'Light')
    
    # Theme configuration
    themes = {
        'Light': {
            'bg': '#f8f9fa',
            'card_bg': '#ffffff',
            'text': '#212529',
            'border': '#ced4da',
            'input_focus': '#80bdff'
        },
        'Dark': {
            'bg': '#0e1117',
            'card_bg': '#1a1c24',
            'text': '#e0e0e0',
            'border': '#30363d',
            'input_focus': '#1f6feb'
        },
        'Ocean': {
            'bg': '#f0f4f8',
            'card_bg': '#ffffff',
            'text': '#102a43',
            'border': '#bcccdc',
            'input_focus': '#48bb78'
        }
    }
    
    t = themes.get(theme, themes['Light'])
    
    st.markdown(f"""
        <style>
        /* Base page background */
        .stApp {{
            background-color: {t['bg']};
        }}
        
        /* Premium look for buttons */
        .stButton>button {{
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.2s;
        }}
        
        /* High contrast for form inputs as requested */
        div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="textarea"] {{
            border: 2px solid {t['border']} !important;
            border-radius: 6px !important;
        }}
        
        div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within {{
            border-color: {t['input_focus']} !important;
            box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.15) !important;
        }}

        /* Better contrast for labels */
        .stMarkdown label p {{
            font-weight: 600 !important;
            color: {t['text']} !important;
        }}
        
        /* Card effect for expanders */
        .streamlit-expanderHeader {{
            background-color: {t['card_bg']};
            border: 1px solid {t['border']};
            border-radius: 8px !important;
            margin-bottom: 0.5rem;
        }}
        
        .streamlit-expanderContent {{
            border: 1px solid {t['border']};
            border-top: none;
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
            padding: 1rem !important;
            background-color: {t['card_bg']};
        }}
        </style>
    """, unsafe_allow_html=True)

def ensure_date(d):
    """Helper to convert various inputs to date object"""
    if not d: return None
    if isinstance(d, datetime.date) and not isinstance(d, datetime.datetime): return d
    if isinstance(d, datetime.datetime): return d.date()
    if isinstance(d, str):
        try: return datetime.date.fromisoformat(d.split('T')[0])
        except: return None
    return None

def ensure_datetime(d, time_str="00:00"):
    """Combine date with time string HH:MM into datetime"""
    if not d: return None
    if isinstance(d, datetime.datetime): return d
    base_date = ensure_date(d)
    if not base_date: return None
    try:
        # Handle cases where people might pass a range instead of a single point
        if '-' in time_str: time_str = time_str.split('-')[0].strip()
        H, M = map(int, time_str.split(':'))
        return datetime.datetime.combine(base_date, datetime.time(H, M))
    except:
        return datetime.datetime.combine(base_date, datetime.time(0, 0))

def get_granular_intervals(start, end, hours_info=None, default_hours="09:00-17:00"):
    """
    Expands a date range into a list of (start_dt, end_dt) based on hourly schedules.
    Supports comma separated intervals like '09:00-11:00, 14:00-18:00'.
    Used for standardized Gantt chart visualizations across the app.
    """
    s_date = ensure_date(start)
    e_date = ensure_date(end)
    if not s_date or not e_date: return []

    intervals_out = []
    curr = s_date
    while curr <= e_date:
        day_str = curr.isoformat()
        h_ranges_str = "00:00-24:00" # Full day default

        if isinstance(hours_info, str) and '-' in hours_info:
            h_ranges_str = hours_info
        elif isinstance(hours_info, dict):
            day_data = hours_info.get(day_str)
            if day_data and isinstance(day_data, dict):
                if not day_data.get('checked', True):
                    curr += datetime.timedelta(days=1)
                    continue
                h_ranges_str = day_data.get('hours', default_hours)
            else:
                h_ranges_str = default_hours
        elif hours_info is not None:
             # If hours_info exists but is not a string/dict, use default
             h_ranges_str = default_hours

        # Process the hours string
        day_intervals = [i.strip() for i in h_ranges_str.split(',') if '-' in i]
        for interval in day_intervals:
            try:
                t1, t2 = interval.split('-')
                seg_start = ensure_datetime(curr, t1)
                
                # Handle 24:00/00:00 end of day logic
                if t2.strip() in ["00:00", "24:00"]:
                    seg_end = ensure_datetime(curr + datetime.timedelta(days=1), "00:00")
                else:
                    seg_end = ensure_datetime(curr, t2)
                
                if seg_end > seg_start:
                    intervals_out.append((seg_start, seg_end))
            except:
                continue
        
        curr += datetime.timedelta(days=1)
    
    return intervals_out
