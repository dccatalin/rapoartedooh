#!/bin/bash
# Script pentru oprirea serverului Streamlit

echo "Se oprește serverul Streamlit..."
pkill -f "streamlit run web_app/Home.py"

if [ $? -eq 0 ]; then
    echo "Serverul a fost oprit."
else
    echo "Nu s-a găsit niciun server Streamlit activ."
fi
