#!/bin/bash
# Script pentru pornirea serverului Streamlit pe serverul Apache (ca Reverse Proxy)

# 1. Navigare în folderul rădăcină (opțional, dacă rulezi manual)
# cd /cale/catre/proiect

# 2. Activare mediu virtual (dacă există)
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 3. Pornire Streamlit
# --server.port 8501: Portul standard Streamlit
# --server.address 0.0.0.0: Permite accesul din rețea
streamlit run web_app/Home.py --server.port 8501 --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false
