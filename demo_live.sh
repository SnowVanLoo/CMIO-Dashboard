#!/bin/bash
# CMIO Command Center — Live Snowflake Demo
SNOWFLAKE_CONNECTION_NAME=Snowflake python3 -m streamlit run "$(dirname "$0")/streamlit_app.py" --server.port 8501
