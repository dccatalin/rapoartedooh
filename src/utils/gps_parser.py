import pandas as pd
import io
import re
import datetime


def parse_gps_log(file_content, filename=""):
    """
    Parses various GPS log formats.
    Returns a dictionary with:
        'total_distance' : float  – km
        'pings'          : int
        'format'         : str
        'gps_points'     : list[{'lat': float, 'lon': float, 'timestamp': str, 'address': str}]
        'date_start'     : str | None  – ISO date "YYYY-MM-DD"
        'date_end'       : str | None
    """
    empty = {'total_distance': 0.0, 'pings': 0, 'format': 'empty',
             'gps_points': [], 'date_start': None, 'date_end': None}
    if not file_content:
        return empty

    filename = (filename or "").lower()

    # 1. Excel format (includes EasyTrackMap .xls exports)
    if filename.endswith(".xls") or filename.endswith(".xlsx"):
        return _parse_excel(file_content)

    # 2. String formats
    content_str = ""
    if isinstance(file_content, bytes):
        try:
            content_str = file_content.decode('utf-8')
        except Exception:
            content_str = file_content.decode('iso-8859-1')
    else:
        content_str = file_content

    lines = [l.strip() for l in content_str.splitlines() if l.strip()]

    # Text-based EasyTrackMap (pasted TSV)
    if any("Timpul plec" in l for l in lines[:5]):
        return _parse_easytrack_text(content_str)

    # 3. Try standard simple CSV (timestamp, lat, lon, speed, distance)
    try:
        df = pd.read_csv(io.StringIO(content_str))
        if 'distance' in df.columns:
            pts = _extract_csv_points(df)
            dates = _extract_dates_csv(df)
            return {
                'total_distance': float(df['distance'].sum()),
                'pings': len(df),
                'format': 'standard_csv',
                'gps_points': pts,
                **dates
            }
        if 'latitude' in df.columns or 'lat' in df.columns:
            pts = _extract_csv_points(df)
            dates = _extract_dates_csv(df)
            return {
                'total_distance': len(df) * 0.1,
                'pings': len(df),
                'format': 'points_only_csv',
                'gps_points': pts,
                **dates
            }
    except Exception:
        pass

    return {**empty, 'format': 'unknown'}


# ---------------------------------------------------------------------------
# GPS point helpers
# ---------------------------------------------------------------------------

def _parse_coord_string(s):
    """Parse '44,410587; 26,054817' or '44.410587, 26.054817' into (lat, lon)."""
    if not s or not isinstance(s, str):
        return None, None
    s = s.strip().replace(',', '.')
    parts = re.split(r'[;|]+', s)
    if len(parts) == 2:
        try:
            return float(parts[0].strip()), float(parts[1].strip())
        except ValueError:
            pass
    return None, None


def _ts_to_str(ts):
    """Convert datetime / date / string to ISO string."""
    if ts is None:
        return None
    if isinstance(ts, (datetime.datetime, datetime.date)):
        return ts.isoformat()
    return str(ts)


def _extract_csv_points(df):
    lat_col = 'latitude' if 'latitude' in df.columns else ('lat' if 'lat' in df.columns else None)
    lon_col = 'longitude' if 'longitude' in df.columns else ('lon' if 'lon' in df.columns else None)
    ts_col = 'timestamp' if 'timestamp' in df.columns else None
    pts = []
    if lat_col and lon_col:
        for _, row in df.iterrows():
            try:
                pts.append({
                    'lat': float(row[lat_col]),
                    'lon': float(row[lon_col]),
                    'timestamp': str(row[ts_col]) if ts_col else None,
                    'address': ''
                })
            except Exception:
                pass
    return pts


def _extract_dates_csv(df):
    ts_col = 'timestamp' if 'timestamp' in df.columns else None
    if not ts_col:
        return {'date_start': None, 'date_end': None}
    try:
        dates = pd.to_datetime(df[ts_col], errors='coerce').dropna()
        return {
            'date_start': dates.min().date().isoformat() if not dates.empty else None,
            'date_end': dates.max().date().isoformat() if not dates.empty else None,
        }
    except Exception:
        return {'date_start': None, 'date_end': None}


# ---------------------------------------------------------------------------
# Excel (EasyTrackMap XLS)
# ---------------------------------------------------------------------------

def _parse_excel(file_bytes):
    """Parses actual Excel files, which EasyTrackMap generates."""
    from src.utils.i18n import remove_diacritics
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), header=None)

        # Find the header row by searching for 'distanta' or 'distance'
        header_idx = -1
        for idx, row in df.iterrows():
            row_str = " ".join([str(val).lower() for val in row.values])
            row_str_clean = remove_diacritics(row_str)
            if "distanta" in row_str_clean or "distance" in row_str_clean:
                header_idx = idx
                break

        if header_idx < 0:
            return {'total_distance': 0.0, 'pings': 0, 'format': 'excel_header_not_found',
                    'gps_points': [], 'date_start': None, 'date_end': None}

        df.columns = df.iloc[header_idx]
        df = df.iloc[header_idx + 1:].reset_index(drop=True)

        # Clean column names
        df.columns = [remove_diacritics(str(c)).strip().lower() for c in df.columns]

        # Identify distance column
        target_col = None
        candidates = ["distanta parcursa", "distanta", "distance", "km"]
        for c in candidates:
            matched_cols = [col for col in df.columns if c in col]
            if matched_cols:
                target_col = matched_cols[0]
                break

        if not target_col:
            return {'total_distance': 0.0, 'pings': 0, 'format': 'excel_no_dist_col',
                    'gps_points': [], 'date_start': None, 'date_end': None}

        # Drop trailing summary rows
        df = df[df[target_col].notna()]
        df = df[df[target_col].astype(str).str.strip() != '-']

        def clean_val(v):
            v_str = str(v).strip()
            if not v_str or v_str in ('-', '~'):
                return 0.0
            v_str = v_str.split()[0]
            v_str = v_str.replace(',', '.')
            try:
                return float(re.sub(r'[^\d.]', '', v_str))
            except Exception:
                return 0.0

        total_dist = df[target_col].apply(clean_val).sum()

        # --- Extract GPS points ---
        gps_points = []
        # Find coordinate and timestamp columns
        coord_start_col = next((c for c in df.columns if 'coordonata' in c and 'porn' in c), None)
        coord_end_col = next((c for c in df.columns if 'coordonata' in c and ('sosire' in c or 'final' in c)), None)
        ts_start_col = next((c for c in df.columns if 'plecar' in c and 'timp' in c), None)
        addr_start_col = next((c for c in df.columns if 'plecare' in c and 'coordonata' not in c), None)

        if not coord_start_col:
            # Fallback: look for any col containing 'coordonata'
            coord_cols = [c for c in df.columns if 'coordonata' in c]
            if coord_cols:
                coord_start_col = coord_cols[0]
                coord_end_col = coord_cols[1] if len(coord_cols) > 1 else None

        for _, row in df.iterrows():
            # Departure point
            if coord_start_col:
                lat, lon = _parse_coord_string(str(row[coord_start_col]))
                if lat is not None:
                    gps_points.append({
                        'lat': lat,
                        'lon': lon,
                        'timestamp': _ts_to_str(row.get(ts_start_col)) if ts_start_col else None,
                        'address': str(row[addr_start_col]) if addr_start_col else ''
                    })
            # Arrival point
            if coord_end_col:
                lat, lon = _parse_coord_string(str(row[coord_end_col]))
                if lat is not None:
                    gps_points.append({
                        'lat': lat,
                        'lon': lon,
                        'timestamp': None,
                        'address': ''
                    })

        # --- Date range ---
        date_start, date_end = None, None
        if ts_start_col and not df.empty:
            ts_vals = pd.to_datetime(df[ts_start_col], errors='coerce').dropna()
            if not ts_vals.empty:
                date_start = ts_vals.min().date().isoformat()
                date_end = ts_vals.max().date().isoformat()
        
        # Fallback: try arrival timestamp column
        if not date_start:
            ts_end_col = next((c for c in df.columns if 'tmpul sosirii' in c or 'sosirii' in c), None)
            if ts_end_col:
                ts_vals = pd.to_datetime(df[ts_end_col], errors='coerce').dropna()
                if not ts_vals.empty:
                    date_start = ts_vals.min().date().isoformat()
                    date_end = ts_vals.max().date().isoformat()

        return {
            'total_distance': float(total_dist),
            'pings': len(df),
            'format': 'easytrackmap_xls',
            'gps_points': gps_points,
            'date_start': date_start,
            'date_end': date_end,
        }

    except Exception as e:
        print(f"Excel Parse Error: {e}")

    return {'total_distance': 0.0, 'pings': 0, 'format': 'excel_fail',
            'gps_points': [], 'date_start': None, 'date_end': None}


# ---------------------------------------------------------------------------
# EasyTrackMap text (TSV)
# ---------------------------------------------------------------------------

def _parse_easytrack_text(content_str):
    from src.utils.i18n import remove_diacritics
    try:
        df = pd.read_csv(io.StringIO(content_str), sep=None, engine='python', skipinitialspace=True)
        df.columns = [remove_diacritics(str(c)).strip() for c in df.columns]

        target_col = None
        candidates = ["Distanta parcursa", "Distanta", "Distance"]
        for c in candidates:
            if c in df.columns:
                target_col = c
                break
        if not target_col:
            for col in df.columns:
                if "Distanta" in col:
                    target_col = col
                    break

        if target_col:
            vals = df[target_col].astype(str)

            def clean_val(v):
                if v in ('-', '~'):
                    return 0.0
                v = v.split()[0]
                v = v.replace(',', '.')
                try:
                    return float(re.sub(r'[^\d.]', '', v))
                except Exception:
                    return 0.0

            total_dist = vals.apply(clean_val).sum()

            # Try to extract GPS points from coord columns if present
            gps_points = []
            coord_col = next((c for c in df.columns if 'Coordonata' in c), None)
            ts_col = next((c for c in df.columns if 'Timp' in c and 'plecar' in c.lower()), None)
            if coord_col:
                for _, row in df.iterrows():
                    lat, lon = _parse_coord_string(str(row[coord_col]))
                    if lat is not None:
                        gps_points.append({
                            'lat': lat, 'lon': lon,
                            'timestamp': _ts_to_str(row.get(ts_col)) if ts_col else None,
                            'address': ''
                        })

            # Date range
            date_start, date_end = None, None
            if ts_col:
                ts_vals = pd.to_datetime(df[ts_col], errors='coerce').dropna()
                if not ts_vals.empty:
                    date_start = ts_vals.min().date().isoformat()
                    date_end = ts_vals.max().date().isoformat()

            return {
                'total_distance': float(total_dist),
                'pings': len(df),
                'format': 'easytrackmap_text',
                'gps_points': gps_points,
                'date_start': date_start,
                'date_end': date_end,
            }
    except Exception:
        pass

    return {'total_distance': 0.0, 'pings': 0, 'format': 'easytrack_text_fail',
            'gps_points': [], 'date_start': None, 'date_end': None}
