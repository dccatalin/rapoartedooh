"""
GPS Route Map Generator
=======================
Generates a PNG image of GPS route points grouped by day,
using matplotlib only (no external tile/API dependency).

Each day gets a distinct color. Points are connected with
polylines in chronological order.
"""

import os
import tempfile
import hashlib
import datetime
from typing import List, Dict, Any

# Distinctive palette for up to 10 days
_DAY_COLORS = [
    '#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6',
    '#1abc9c', '#e67e22', '#34495e', '#e91e63', '#00bcd4'
]


def generate_route_map(gps_points: List[Dict[str, Any]], output_path: str = None) -> str | None:
    """
    Generate a PNG route map from a list of GPS point dicts.
    """
    if not gps_points:
        return None

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from datetime import datetime
        import PIL.Image
        import requests
        import io
        import math
    except ImportError:
        return None

    def deg2num(lat_deg, lon_deg, zoom):
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        xtile = int((lon_deg + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
        return (xtile, ytile)

    def num2deg(xtile, ytile, zoom):
        n = 2.0 ** zoom
        lon_deg = xtile / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
        lat_deg = math.degrees(lat_rad)
        return (lat_deg, lon_deg)

    # 1. Background Logic: Try API first, then OSM
    from src.data.company_settings import CompanySettings
    from src.utils.map_service import MapService
    settings = CompanySettings().get_settings()
    ms = MapService(google_key=settings.get('google_maps_api_key'), 
                    mapbox_key=settings.get('mapbox_api_key'))
    
    api_map_url = ms.get_static_route_map_url(gps_points)
    if api_map_url and ms.download_static_map(api_map_url, output_path or 'static_map.png'):
        return output_path or 'static_map.png'

    # 2. Fallback to OSM tiles with matplotlib
    day_map: Dict[str, List[Dict]] = {}
    for pt in gps_points:
        ts = pt.get('timestamp') or ''
        day = ts[:10] if ts and len(ts) >= 10 else 'unknown'
        day_map.setdefault(day, []).append(pt)

    days = sorted(day_map.keys())

    # Get bounds
    lats = [p['lat'] for p in gps_points if p.get('lat') is not None]
    lons = [p['lon'] for p in gps_points if p.get('lon') is not None]
    if not lats: return None
    
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    
    # Padding
    lat_pad = (max_lat - min_lat) * 0.1 or 0.01
    lon_pad = (max_lon - min_lon) * 0.1 or 0.01
    min_lat, max_lat = min_lat - lat_pad, max_lat + lat_pad
    min_lon, max_lon = min_lon - lon_pad, max_lon + lon_pad

    # Determine zoom
    zoom = 13
    if (max_lat - min_lat) > 0.5: zoom = 10
    elif (max_lat - min_lat) > 0.1: zoom = 12

    xtile_min, ytile_min = deg2num(max_lat, min_lon, zoom)
    xtile_max, ytile_max = deg2num(min_lat, max_lon, zoom)

    # Limit tiles to avoid huge requests
    xtile_max = min(xtile_max, xtile_min + 5)
    ytile_max = min(ytile_max, ytile_min + 5)

    # Stitch tiles
    width, height = (xtile_max - xtile_min + 1) * 256, (ytile_max - ytile_min + 1) * 256
    canvas = PIL.Image.new('RGB', (width, height))
    
    headers = {'User-Agent': 'AntigravityPoPReport/1.0'}
    for x in range(xtile_min, xtile_max + 1):
        for y in range(ytile_min, ytile_max + 1):
            url = f"https://tile.openstreetmap.org/{zoom}/{x}/{y}.png"
            try:
                r = requests.get(url, headers=headers, timeout=5)
                if r.status_code == 200:
                    tile = PIL.Image.open(io.BytesIO(r.content))
                    canvas.paste(tile, ((x - xtile_min) * 256, (y - ytile_min) * 256))
            except:
                pass

    # Map bounds in degrees for imshow
    nw_lat, nw_lon = num2deg(xtile_min, ytile_min, zoom)
    se_lat, se_lon = num2deg(xtile_max + 1, ytile_max + 1, zoom)

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.imshow(canvas, extent=(nw_lon, se_lon, se_lat, nw_lat), alpha=0.9, zorder=0)

    legend_patches = []
    for i, day in enumerate(days):
        color = _DAY_COLORS[i % len(_DAY_COLORS)]
        pts = day_map[day]
        
        # Sort points by timestamp if available
        try:
            pts = sorted(pts, key=lambda x: x.get('timestamp', ''))
        except:
            pass

        # Segment route by time gap (e.g. 10 minutes)
        segments = []
        current_segment = []
        last_ts = None
        
        for pt in pts:
            if pt.get('lat') is None or pt.get('lon') is None:
                continue
                
            ts_str = pt.get('timestamp')
            try:
                ts = datetime.fromisoformat(ts_str.replace('Z', '')) if ts_str else None
            except:
                ts = None
                
            if last_ts and ts and (ts - last_ts).total_seconds() > 600: # 10 minutes gap
                if current_segment:
                    segments.append(current_segment)
                current_segment = []
            
            current_segment.append(pt)
            last_ts = ts
            
        if current_segment:
            segments.append(current_segment)

        if not segments:
            continue

        # Plot each segment
        for j, seg in enumerate(segments):
            lats = [p['lat'] for p in seg]
            lons = [p['lon'] for p in seg]
            
            # Bottom layer: Dark border for the line (gives a "stroke" effect)
            ax.plot(lons, lats, '-', color='white', linewidth=4.5, alpha=0.6, zorder=3)
            # Middle layer: Main colored line
            ax.plot(lons, lats, '-', color=color, linewidth=2.8, alpha=0.9, zorder=4)
            
            # Draw points (smaller)
            ax.plot(lons, lats, 'o', color=color, markersize=2.0, alpha=0.5, zorder=5)
            
            # Start / end markers for the WHOLE day
            if j == 0:
                ax.plot(lons[0], lats[0], 's', color=color, markersize=10, 
                        markeredgecolor='white', markeredgewidth=1.5, zorder=10)
            if j == len(segments) - 1:
                ax.plot(lons[-1], lats[-1], '^', color=color, markersize=12, 
                        markeredgecolor='white', markeredgewidth=1.5, zorder=10)

    ax.set_xlabel('Longitudine', color='#333', fontsize=10)
    ax.set_ylabel('Latitudine', color='#333', fontsize=10)
    ax.set_title('Traseu GPS — Detalii Rute Auditate', color='#0d47a1', fontsize=14, pad=15, fontweight='bold')
    
    # Grid styling (subtle since we have tiles)
    ax.grid(True, linestyle='--', alpha=0.3, color='black')
    for spine in ax.spines.values():
        spine.set_edgecolor('#ccc')

    if legend_patches:
        legend = ax.legend(handles=legend_patches, loc='upper right',
                           facecolor='white', edgecolor='#0d47a1',
                           shadow=True, fontsize=9, framealpha=0.9)

    plt.tight_layout(pad=1.5)

    if output_path is None:
        h = hashlib.md5(str(gps_points[:5]).encode()).hexdigest()[:8]
        output_path = os.path.join(tempfile.gettempdir(), f'route_map_{h}.png')

    plt.savefig(output_path, dpi=120, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    return output_path
