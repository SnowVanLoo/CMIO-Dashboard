#!/bin/bash
# CMIO Command Center — Offline Demo (no Snowflake needed)
OFFLINE_MODE=true python3 -m streamlit run "$(dirname "$0")/streamlit_app.py" --server.port 8501
