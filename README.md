# CMIO Command Center

A Streamlit demo showing how Snowflake unifies Epic EHR, Workday HCM, payer claims, and SDOH data into a clinical informatics command center for health system CMIOs.

## Overview

**MetroHealth Alliance** — 12 hospitals, 115 clinics, 220 providers, $3.8B revenue

### 4 Tabs
1. **Clinical Quality & Outcomes** — Readmission rates, HCAHPS, HAI, doc completion, department scorecards
2. **Payer & Claims Intelligence** — Denial rates by payer, revenue waterfall, denial code treemap, service line performance
3. **SDOH & Population Health** — Community risk scoring, social determinants, chronic condition prevalence by ZIP
4. **AI & Technology ROI** — DAX ambient AI adoption, after-hours reduction, ROI calculator, Cortex AI executive briefing

### Features
- Sidebar Cortex AI Q&A chat (always accessible)
- Date range + facility + department filters
- Gauge charts, treemaps, sunburst, waterfall, gradient area charts
- Custom HTML KPI cards with delta indicators
- Offline mode via DuckDB + Parquet (no Snowflake needed for demos)

## Data Sources
- **Epic EHR** — EHR usage, clinical outcomes, provider burnout metrics
- **Workday HCM** — Training/LMS completion, department data
- **Payer Claims** — 8,500 synthetic claims across 7 payers, 8 service lines
- **SDOH** — 780 rows across 10 ZIP codes, 6 chronic conditions
- **IT Operations** — Support tickets, system downtime

## Setup

### Requirements
```
streamlit
plotly
pandas
snowflake-snowpark-python
```

### Run (Live — Snowflake)
```bash
SNOWFLAKE_CONNECTION_NAME=<your_connection> python3 -m streamlit run streamlit_app.py --server.port 8501
```
Or use the launch script:
```bash
./demo_live.sh
```

### Run (Offline — no Snowflake needed)
```bash
OFFLINE_MODE=true python3 -m streamlit run streamlit_app.py --server.port 8501
```
Or:
```bash
./demo_offline.sh
```
> Note: Parquet data files (`data/*.parquet`) are excluded from this repo. Generate them by running the app once with a live Snowflake connection, or export from: `TEMP.<YOUR_SCHEMA>.{TABLE_NAME}`.

### Snowflake Schema
Tables live in `TEMP.TVANLOO_CMIO_COMMAND_CENTER`:
- `FACILITIES` (12 rows)
- `DEPARTMENTS` (15 rows)
- `PROVIDERS` (220 rows)
- `EHR_DAILY_USAGE` (45,662 rows)
- `CLINICAL_OUTCOMES` (2,160 rows)
- `TRAINING_LMS` (2,640 rows)
- `SUPPORT_TICKETS` (2,475 rows)
- `SYSTEM_DOWNTIME` (208 rows)
- `VBC_METRICS` (2,340 rows)
- `PAYER_CLAIMS` (8,500 rows)
- `SDOH_POPULATION` (780 rows)

## Powered By
- [Snowflake](https://snowflake.com) — Data platform
- [Cortex AI](https://docs.snowflake.com/en/user-guide/cortex) — `mistral-large2` for Q&A and executive briefing
- [Streamlit](https://streamlit.io) — App framework
- [Plotly](https://plotly.com) — Interactive charts
