import pandas as pd
import io
import re

def parse_gps_log(file_content, filename=""):
    """
    Parses various GPS log formats.
    Returns a dictionary with:
        'total_distance': float,
        'pings': int,
        'format': str
    """
    if not file_content:
        return {'total_distance': 0.0, 'pings': 0, 'format': 'empty'}

    filename = (filename or "").lower()

    # 1. Excel format (includes EasyTrackMap .xls exports)
    if filename.endswith(".xls") or filename.endswith(".xlsx"):
        return _parse_excel(file_content)

    # 2. String formats
    content_str = ""
    if isinstance(file_content, bytes):
        try:
            content_str = file_content.decode('utf-8')
        except:
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
            return {
                'total_distance': float(df['distance'].sum()),
                'pings': len(df),
                'format': 'standard_csv'
            }
        # Fallback: if it has lat/lon but no distance
        if 'latitude' in df.columns or 'lat' in df.columns:
            return {
                'total_distance': len(df) * 0.1,
                'pings': len(df),
                'format': 'points_only_csv'
            }
    except:
        pass

    return {'total_distance': 0.0, 'pings': 0, 'format': 'unknown'}

def _parse_excel(file_bytes):
    """Parses actual Excel files, which EasyTrackMap generates."""
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), header=None)
        
        # Find the header row by searching for 'distanta' or 'distance'
        header_idx = -1
        for idx, row in df.iterrows():
            row_str = " ".join([str(val).lower() for val in row.values])
            from src.utils.i18n import remove_diacritics
            row_str_clean = remove_diacritics(row_str)
            if "distanta" in row_str_clean or "distance" in row_str_clean:
                header_idx = idx
                break
                
        if header_idx >= 0:
            df.columns = df.iloc[header_idx]
            df = df.iloc[header_idx+1:].reset_index(drop=True)
            
            # Clean column names
            from src.utils.i18n import remove_diacritics
            df.columns = [remove_diacritics(str(c)).strip().lower() for c in df.columns]
        else:
            return {'total_distance': 0.0, 'pings': 0, 'format': 'excel_header_not_found'}        
        # Identify the correct column for distance
        target_col = None
        candidates = ["distanta parcursa", "distanta", "distance", "km"]
        for c in candidates:
            # Check for exact or partial matches
            matched_cols = [col for col in df.columns if c in col]
            if matched_cols:
                # If multiple, prefer the exact one, otherwise the first
                target_col = matched_cols[0]
                break

        if target_col:
            # Drop trailing summary rows if any (e.g. index with '-')
            df = df[df[target_col].notna()]
            df = df[df[target_col].astype(str).str.strip() != '-']
            
            # Clean and sum up
            def clean_val(v):
                v_str = str(v).strip()
                if not v_str or v_str == '-' or v_str == '~': return 0.0
                v_str = v_str.split()[0] # Handle "1.5 km"
                v_str = v_str.replace(',', '.')
                try:
                    return float(re.sub(r'[^\d.]', '', v_str))
                except:
                    return 0.0
            
            total_dist = df[target_col].apply(clean_val).sum()
            return {
                'total_distance': float(total_dist),
                'pings': len(df),
                'format': 'easytrackmap_xls'
            }
    except Exception as e:
        print(f"Excel Parse Error: {e}")
        
    return {'total_distance': 0.0, 'pings': 0, 'format': 'excel_fail'}

def _parse_easytrack_text(content_str):
    """
    Parses EasyTrackMap text export (TSV).
    """
    try:
        df = pd.read_csv(io.StringIO(content_str), sep=None, engine='python', skipinitialspace=True)
        from src.utils.i18n import remove_diacritics
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
                if v == '-' or v == '~': return 0.0
                v = v.split()[0]
                v = v.replace(',', '.')
                try:
                    return float(re.sub(r'[^\d.]', '', v))
                except:
                    return 0.0
            
            total_dist = vals.apply(clean_val).sum()
            return {
                'total_distance': float(total_dist),
                'pings': len(df),
                'format': 'easytrackmap_text'
            }
    except:
        pass

    return {'total_distance': 0.0, 'pings': 0, 'format': 'easytrack_text_fail'}
