"""
VnNox Play Log Parser
=====================
Supports two CSV export formats produced by the VnNox platform.

Format 1 – Play Logs(Details):
    Columns: Media Name, Screen Name, Start Date, End Date, Duration（s）
    One row per individual play event.

Format 2 – Play Logs(Overview):
    Columns: Media Name, Screen Name, Start Date, End Date,
             Total Duration (s), Times, Total Days
    One row per media item (summarised).

Both formats wrap every cell with VnNox's Excel-injection prefix:
    =(""value"")
This parser strips that wrapper before processing.
"""

import re
import io
import csv
import logging
from typing import IO, Dict, Any

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_VNNOX_CELL_RE = re.compile(r'^=\(\s*"(.*?)"\s*\)$', re.DOTALL)


def _clean(value: str) -> str:
    """Strip VnNox Excel-injection wrapper from a single cell value.
    
    Handles both:
      =("value")         ← actual CSV on disk after csv.reader parsing
      =("value")         ← when the outer quotes are still present
    """
    value = value.strip()
    m = _VNNOX_CELL_RE.match(value)
    if m:
        return m.group(1).strip()
    # Strip any remaining surrounding quotes
    return value.strip('"').strip("'").strip()


def _normalize_header(h: str) -> str:
    """Lower-case, strip unicode noise, collapse whitespace."""
    h = _clean(h)
    # remove non-ascii invisible chars (e.g. BOM, narrow no-break space)
    h = re.sub(r'[^\x20-\x7e]', ' ', h)
    return ' '.join(h.lower().split())


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def parse_vnnox_csv(file_obj: IO[bytes]) -> Dict[str, Any]:
    """
    Parse a VnNox Play Logs CSV (Details OR Overview) file.

    Parameters
    ----------
    file_obj : file-like object with .read() returning bytes

    Returns
    -------
    dict with keys:
        format        : 'details' | 'overview'
        total_seconds : float  – total playback time in seconds
        total_hours   : float  – total_seconds / 3600
        total_spots   : int    – number of play events
        rows          : list[dict] – cleaned row data
        errors        : list[str]  – any non-fatal parse warnings
    """
    raw = file_obj.read()

    # Detect encoding (VnNox often exports with UTF-8 BOM)
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw.decode('latin-1')

    reader = csv.reader(io.StringIO(text))
    all_rows = list(reader)

    if not all_rows:
        raise ValueError("Fisierul este gol sau nu poate fi citit ca CSV.")

    # --- Detect header row ------------------------------------------
    # The header row is the first row that contains recognisable column names.
    header_idx = None
    headers_raw = []
    for i, row in enumerate(all_rows):
        cleaned = [_normalize_header(c) for c in row]
        if 'media name' in cleaned and ('duration (s)' in cleaned
                                         or 'total duration (s)' in cleaned
                                         or 'duration s' in cleaned):
            header_idx = i
            headers_raw = cleaned
            break

    if header_idx is None:
        raise ValueError(
            "Nu s-a gasit randul de antet. Asigurati-va ca fisierul este "
            "exportat din VnNox (Play Logs - Details sau Overview)."
        )

    data_rows = all_rows[header_idx + 1:]

    # --- Detect format ----------------------------------------------
    # Overview has 'total duration (s)' or 'times' column
    is_overview = ('total duration (s)' in headers_raw
                   or 'times' in headers_raw)

    fmt = 'overview' if is_overview else 'details'

    # Helper: map column name -> index (tolerant matching)
    def col_idx(candidates):
        for c in candidates:
            for i, h in enumerate(headers_raw):
                if c in h:
                    return i
        return None

    errors = []
    rows = []
    total_seconds = 0.0
    total_spots = 0

    if fmt == 'overview':
        dur_col = col_idx(['total duration (s)', 'duration (s)', 'duration s'])
        times_col = col_idx(['times'])
        if dur_col is None:
            raise ValueError("Nu s-a gasit coloana 'Total Duration (s)' in fisierul Overview.")

        for i, row in enumerate(data_rows):
            if len(row) <= max(filter(None, [dur_col, times_col or 0])):
                continue
            try:
                dur_str = _clean(row[dur_col]).replace(',', '').replace(' ', '')
                if not dur_str:
                    continue
                dur = float(dur_str)
                spots = int(_clean(row[times_col])) if times_col is not None and times_col < len(row) else 1
                total_seconds += dur
                total_spots += spots
                rows.append({c: _clean(row[j]) for j, c in enumerate(headers_raw) if j < len(row)})
            except (ValueError, IndexError) as e:
                errors.append(f"Rand {header_idx + 2 + i}: {e}")

    else:  # details
        dur_col = col_idx(['duration', 'duration s'])
        if dur_col is None:
            raise ValueError("Nu s-a gasit coloana 'Duration (s)' in fisierul Details.")

        for i, row in enumerate(data_rows):
            if not row or all(c.strip() in ('', '=""') for c in row):
                continue
            if dur_col >= len(row):
                continue
            try:
                dur_str = _clean(row[dur_col]).replace(',', '').replace(' ', '')
                if not dur_str:
                    continue
                dur = float(dur_str)
                total_seconds += dur
                total_spots += 1
                rows.append({c: _clean(row[j]) for j, c in enumerate(headers_raw) if j < len(row)})
            except (ValueError, IndexError) as e:
                errors.append(f"Rand {header_idx + 2 + i}: {e}")

    if not rows:
        raise ValueError(
            "Niciun rand valid nu a putut fi procesat. "
            "Verificati ca fisierul contine date de tip 'Play Log'."
        )

    total_hours = total_seconds / 3600.0

    # --- Build per-spot summary (media name level) ---
    from collections import defaultdict
    spot_map = defaultdict(lambda: {'plays': 0, 'total_seconds': 0.0,
                                     'date_start': None, 'date_end': None, 'screen': ''})

    start_col = col_idx(['start date', 'start'])
    end_col_name = col_idx(['end date', 'end'])
    media_col = col_idx(['media name'])
    screen_col = col_idx(['screen name', 'screen'])

    for row in rows:
        # Identify spot key
        m_name = row.get('media name', 'Unknown')
        if not m_name:
            m_name = 'Unknown'
        entry = spot_map[m_name]
        entry['screen'] = row.get('screen name', row.get('screen', ''))
        if fmt == 'overview':
            entry['plays'] += int(row.get('times', 0) or 0)
            entry['total_seconds'] += float(row.get('total duration (s)', 0) or 0)
        else:
            entry['plays'] += 1
            dur_key = next((k for k in row if 'duration' in k), None)
            entry['total_seconds'] += float(row.get(dur_key, 0) or 0) if dur_key else 0

        # Date range per spot
        s_val = row.get('start date', row.get('start', ''))
        e_val = row.get('end date', row.get('end', ''))
        if s_val:
            if entry['date_start'] is None or s_val < entry['date_start']:
                entry['date_start'] = s_val[:10]
        if e_val:
            if entry['date_end'] is None or e_val > entry['date_end']:
                entry['date_end'] = e_val[:10]

    spots_summary = []
    for m_name, s in spot_map.items():
        spots_summary.append({
            'media_name': m_name,
            'screen': s['screen'],
            'plays': s['plays'],
            'total_seconds': round(s['total_seconds'], 1),
            'total_hours': round(s['total_seconds'] / 3600, 4),
            'date_start': s['date_start'],
            'date_end': s['date_end'],
        })
    # Sort by date_start
    spots_summary.sort(key=lambda x: (x['date_start'] or ''))

    # --- Overall date range ---
    all_starts = [s['date_start'] for s in spots_summary if s['date_start']]
    all_ends = [s['date_end'] for s in spots_summary if s['date_end']]
    date_start = min(all_starts) if all_starts else None
    date_end = max(all_ends) if all_ends else None

    logger.info(
        "VnNox parse OK | format=%s | spots=%d | duration=%.2f h | errors=%d",
        fmt, total_spots, total_hours, len(errors)
    )

    return {
        'format': fmt,
        'total_seconds': total_seconds,
        'total_hours': round(total_hours, 4),
        'total_spots': total_spots,
        'rows': rows,
        'errors': errors,
        'spots_summary': spots_summary,
        'date_start': date_start,
        'date_end': date_end,
    }
