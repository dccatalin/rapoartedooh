# Mobile DOOH Campaign Report Generator

A standalone PyQt6 application for generating comprehensive Mobile DOOH (Digital Out-of-Home) campaign reports with audience estimation and traffic analysis.

## Features

- **Campaign Configuration Dialog**: Easy-to-use interface for entering campaign details
- **City Database**: Pre-loaded data for major Romanian cities (population, traffic statistics)
- **Automatic Data Integration**: City stats are automatically filled based on selected location
- **Professional PDF Reports**: Includes narrative analysis, charts, and statistical estimations
- **Diacritics Handling**: Automatic removal of Romanian diacritics for proper PDF rendering

## Installation

1. Create a virtual environment (recommended):

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the application:

```bash
python main.py
```

### Generating a Report

1. Click **"Create New Campaign Report"**
2. Fill in the campaign details:
   - Client Name (e.g., "Dr. Max")
   - Campaign Name
   - City (select from dropdown or enter custom)
   - Start and End Dates
   - Daily Hours (e.g., "09:00-17:00")
   - Total Exposure Hours
   - Vehicle Speed and Stationing Time
3. Click **OK** to generate the report
4. The PDF will be automatically saved to the `reports/` directory and opened

## Project Structure

```
rapoartedooh/
├── main.py                          # Application entry point
├── requirements.txt                 # Python dependencies
├── reports/                         # Generated PDF reports (created automatically)
└── src/
    ├── data/
    │   ├── city_profiles.json      # City database
    │   └── city_data_manager.py    # City data management
    ├── reporting/
    │   ├── report_generator.py     # Base report generator (charts, PDF utils)
    │   └── campaign_report_generator.py  # Campaign-specific report logic
    └── ui/
        ├── main_window.py          # Main application window
        └── campaign_report_dialog.py  # Campaign configuration dialog
```

## City Database

The application includes pre-configured data for the following cities:

- București
- Cluj-Napoca
- Timișoara
- Iași
- Constanța
- Brașov
- Craiova
- Galați
- Oradea
- Ploiești

You can add more cities by editing `src/data/city_profiles.json`.

## Requirements

- Python 3.8+
- PyQt6
- ReportLab
- Matplotlib

## License

Proprietary - All rights reserved
