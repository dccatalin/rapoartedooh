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

    Parameters
    ----------
    gps_points : list of dicts with keys: 'lat', 'lon', 'timestamp' (optional)
    output_path : absolute path for output PNG; uses a temp path if None

    Returns
    -------
    Absolute path to the PNG file, or None if generation failed.
    """
    if not gps_points:
        return None

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        return None

    # Group by day
    day_map: Dict[str, List[Dict]] = {}
    for pt in gps_points:
        ts = pt.get('timestamp') or ''
        day = ts[:10] if ts and len(ts) >= 10 else 'unknown'
        day_map.setdefault(day, []).append(pt)

    days = sorted(day_map.keys())

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_facecolor('#1a1a2e')
    fig.patch.set_facecolor('#16213e')

    legend_patches = []
    for i, day in enumerate(days):
        color = _DAY_COLORS[i % len(_DAY_COLORS)]
        pts = day_map[day]
        lats = [p['lat'] for p in pts if p.get('lat') is not None]
        lons = [p['lon'] for p in pts if p.get('lon') is not None]
        if not lats:
            continue
        ax.plot(lons, lats, '-o', color=color, markersize=2.5,
                linewidth=1.2, alpha=0.85, zorder=3)
        # Start / end markers
        ax.plot(lons[0], lats[0], 's', color=color, markersize=7,
                alpha=1.0, zorder=5)
        ax.plot(lons[-1], lats[-1], '^', color=color, markersize=7,
                alpha=1.0, zorder=5)

        day_label = day if day != 'unknown' else 'Data necunoscuta'
        legend_patches.append(mpatches.Patch(color=color, label=day_label))

    ax.set_xlabel('Longitudine', color='white', fontsize=9)
    ax.set_ylabel('Latitudine', color='white', fontsize=9)
    ax.set_title('Traseu GPS — Harta Rutei', color='white', fontsize=12, pad=10)
    ax.tick_params(colors='white', labelsize=7)
    for spine in ax.spines.values():
        spine.set_edgecolor('#444')

    if legend_patches:
        legend = ax.legend(handles=legend_patches, loc='upper right',
                           facecolor='#0f3460', edgecolor='#e94560',
                           labelcolor='white', fontsize=8)

    plt.tight_layout(pad=1.0)

    if output_path is None:
        h = hashlib.md5(str(gps_points[:5]).encode()).hexdigest()[:8]
        output_path = os.path.join(tempfile.gettempdir(), f'route_map_{h}.png')

    plt.savefig(output_path, dpi=120, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close(fig)

    return output_path
