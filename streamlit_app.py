import streamlit as st
st.set_page_config(page_title="CMIO Command Center", layout="wide", page_icon=":material/monitor_heart:")
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os, pathlib

SCHEMA = "TEMP.TVANLOO_CMIO_COMMAND_CENTER"
OFFLINE_MODE = os.getenv("OFFLINE_MODE", "false").lower() == "true"
DATA_DIR = pathlib.Path(__file__).parent / "data"

if OFFLINE_MODE:
    import duckdb
    _duck = duckdb.connect()
    for _tbl in ["FACILITIES","DEPARTMENTS","PROVIDERS","EHR_DAILY_USAGE",
                 "CLINICAL_OUTCOMES","TRAINING_LMS","SUPPORT_TICKETS",
                 "SYSTEM_DOWNTIME","VBC_METRICS","PAYER_CLAIMS","SDOH_POPULATION"]:
        pf = DATA_DIR / f"{_tbl}.parquet"
        if pf.exists():
            _duck.execute(f"CREATE OR REPLACE TABLE {_tbl} AS SELECT * FROM read_parquet('{pf}')")
    IS_SIS = False
    session = None
else:
    session = None
    IS_SIS = False
    try:
        session = st.connection("snowflake").session()
        IS_SIS = True
    except Exception:
        pass
    if session is None:
        try:
            from snowflake.snowpark.context import get_active_session
            session = get_active_session()
            IS_SIS = True
        except Exception:
            pass
    if session is None:
        try:
            from snowflake.snowpark import Session
            conn_name = os.getenv("SNOWFLAKE_CONNECTION_NAME", "Snowflake")
            session = Session.builder.config("connection_name", conn_name).create()
            IS_SIS = False
        except Exception:
            session = None
            IS_SIS = False

if not IS_SIS and not OFFLINE_MODE and session is not None:
    try:
        session.sql("USE ROLE SALES_ENGINEER").collect()
        session.sql("USE WAREHOUSE SNOWADHOC").collect()
    except Exception:
        pass

if session is None and not OFFLINE_MODE:
    st.error("⚠️ No Snowflake connection. To run on Streamlit Cloud, add Snowflake credentials to **Settings → Secrets**.")
    st.stop()

HEALTH_SYSTEM = {
    "name": "MetroHealth Alliance", "hospitals": 12, "clinics": 115,
    "revenue": "$3.8B", "providers": 220, "beds": 3730,
}
AI_ROLLOUT_DATE = "2025-10-01"
P = ["#2563EB","#059669","#D97706","#DC2626","#7C3AED","#0891B2","#EA580C","#65A30D"]


@st.cache_data(ttl=300)
def run_query(sql):
    if OFFLINE_MODE:
        return _duck.execute(sql.replace(f"{SCHEMA}.", "")).df()
    return session.sql(sql).to_pandas()


def safe(val, fmt=".1f", sfx="", fb="--"):
    try:
        if pd.isna(val): return fb
        return f"{val:{fmt}}{sfx}"
    except Exception: return fb


@st.cache_data(ttl=60)
def call_cortex(prompt_text):
    escaped = prompt_text.replace("'", "''")
    return run_query(f"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', '{escaped}') AS SUMMARY")


def kpi_card(label, value, delta=None, delta_color="normal"):
    dh = ""
    if delta:
        neg = str(delta).lstrip().startswith("-")
        if delta_color == "inverse":
            c = "#059669" if neg else "#DC2626"
        elif delta_color == "off":
            c = "#94A3B8"
        else:
            c = "#DC2626" if neg else "#059669"
        arrow = "&#9660;" if neg else "&#9650;"
        dh = f'<div style="font-size:11px;color:{c};margin-top:4px;font-weight:600;">{arrow} {delta}</div>'
    st.markdown(
        f'<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;'
        f'padding:18px 20px;box-shadow:0 1px 6px rgba(0,0,0,0.04);min-height:95px;">'
        f'<div style="font-size:10px;color:#64748B;text-transform:uppercase;letter-spacing:0.08em;'
        f'font-weight:700;margin-bottom:6px;">{label}</div>'
        f'<div style="font-size:26px;font-weight:800;color:#0F172A;line-height:1.1;">{value}</div>'
        f'{dh}</div>', unsafe_allow_html=True)


def gauge_chart(value, title, target=None, color="#2563EB", height=200):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value, title={"text": title, "font": {"size": 13, "color": "#475569"}},
        number={"font": {"size": 28, "color": "#0F172A"}, "suffix": "%"},
        gauge={"axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "#E2E8F0"},
               "bar": {"color": color, "thickness": 0.7},
               "bgcolor": "#F1F5F9", "borderwidth": 0,
               "threshold": {"line": {"color": "#DC2626", "width": 2}, "thickness": 0.8,
                              "value": target} if target else {},
               "steps": [{"range": [0, 40], "color": "#FEE2E2"},
                          {"range": [40, 70], "color": "#FEF9C3"},
                          {"range": [70, 100], "color": "#DCFCE7"}]}))
    fig.update_layout(height=height, margin=dict(l=20,r=20,t=40,b=10), paper_bgcolor="rgba(0,0,0,0)", font={"color": "#475569"})
    return fig


def section_header(icon, title, subtitle=""):
    sh = f'<span style="color:#94A3B8;font-size:12px;margin-left:8px;">{subtitle}</span>' if subtitle else ""
    st.markdown(f'<div style="display:flex;align-items:center;margin:20px 0 10px 0;">'
                f'<span style="font-size:18px;margin-right:8px;">{icon}</span>'
                f'<span style="font-size:16px;font-weight:700;color:#1E293B;">{title}</span>{sh}</div>',
                unsafe_allow_html=True)


def chart_defaults(fig, h=340):
    fig.update_layout(height=h, margin=dict(l=10,r=10,t=30,b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter, system-ui, sans-serif", color="#475569", size=11),
                      legend=dict(orientation="h", y=-0.15, font=dict(size=10)))
    fig.update_xaxes(gridcolor="#F1F5F9", zeroline=False)
    fig.update_yaxes(gridcolor="#F1F5F9", zeroline=False)
    return fig


# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""<style>
.stApp { background: #F8FAFC; }
section[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E2E8F0; }
.stTabs [data-baseweb="tab-list"] { gap: 2px; background: #F1F5F9; padding: 4px 6px; border-radius: 10px; }
.stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 8px 18px; font-size: 13px; font-weight: 500; color: #475569; background: transparent; border: none; }
.stTabs [aria-selected="true"] { background: #FFFFFF !important; color: #1D4ED8 !important; box-shadow: 0 1px 4px rgba(37,99,235,0.12) !important; font-weight: 700 !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }
div[data-testid="stExpander"] { border: 1px solid #E2E8F0; border-radius: 10px; background: #FFFFFF; }
</style>""", unsafe_allow_html=True)


# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#1E3A5F 0%,#2563EB 50%,#3B82F6 100%);
            padding:24px 30px;border-radius:14px;margin-bottom:16px;position:relative;overflow:hidden;">
  <div style="position:absolute;top:-20px;right:-20px;width:120px;height:120px;background:rgba(255,255,255,0.06);border-radius:50%;"></div>
  <div style="position:absolute;bottom:-30px;right:60px;width:80px;height:80px;background:rgba(255,255,255,0.04);border-radius:50%;"></div>
  <h1 style="color:white;margin:0;font-size:26px;font-weight:800;letter-spacing:-0.02em;">
    CMIO Command Center</h1>
  <p style="color:#93C5FD;margin:6px 0 0 0;font-size:13px;font-weight:500;">
    Clinical Informatics Intelligence &nbsp;&bull;&nbsp; MetroHealth Alliance
    &nbsp;&bull;&nbsp; Powered by Snowflake + Cortex AI
  </p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### {HEALTH_SYSTEM['name']}")
    st.caption(f"{HEALTH_SYSTEM['hospitals']} Hospitals • {HEALTH_SYSTEM['clinics']} Clinics • {HEALTH_SYSTEM['providers']} Providers • {HEALTH_SYSTEM['revenue']}")
    st.divider()

    today = datetime.now().date()
    _max = run_query(f"SELECT MAX(USAGE_DATE)::DATE AS DT FROM {SCHEMA}.EHR_DAILY_USAGE")
    data_max = _max["DT"].iloc[0] if not _max.empty else today
    default_end = min(data_max, today)
    default_start = default_end - timedelta(days=365)
    date_range = st.date_input("Date Range", value=(default_start, default_end), key="dr")

    facilities = run_query(f"SELECT FACILITY_ID, FACILITY_NAME FROM {SCHEMA}.FACILITIES ORDER BY FACILITY_ID")
    sel_fac = st.multiselect("Facilities", options=facilities["FACILITY_ID"].tolist(),
        format_func=lambda x: facilities.set_index("FACILITY_ID").loc[x, "FACILITY_NAME"],
        default=None, placeholder="All Facilities")

    departments = run_query(f"SELECT DEPARTMENT_ID, DEPARTMENT_NAME FROM {SCHEMA}.DEPARTMENTS ORDER BY DEPARTMENT_NAME")
    sel_dept = st.multiselect("Departments", options=departments["DEPARTMENT_ID"].tolist(),
        format_func=lambda x: departments.set_index("DEPARTMENT_ID").loc[x, "DEPARTMENT_NAME"],
        default=None, placeholder="All Departments")

    st.divider()

    st.markdown("#### :material/chat: Ask Cortex AI")
    if "qa_history" not in st.session_state:
        st.session_state.qa_history = []

    for qa in st.session_state.qa_history[-3:]:
        st.markdown(f'<div style="background:#EFF6FF;padding:8px 10px;border-radius:8px;margin-bottom:4px;font-size:12px;">'
                    f'<b>Q:</b> {qa["q"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;padding:8px 10px;border-radius:8px;margin-bottom:8px;font-size:12px;line-height:1.6;">'
                    f'{qa["a"][:500]}{"..." if len(qa["a"])>500 else ""}</div>', unsafe_allow_html=True)

    if OFFLINE_MODE:
        st.info("Q&A requires live Snowflake connection.", icon=":material/cloud_off:")
    else:
        with st.form("qa_form", clear_on_submit=True):
            q = st.text_input("Ask about your data", placeholder="e.g. Which payer has highest denial rate?", label_visibility="collapsed")
            c1, c2 = st.columns([3,1])
            ask = c1.form_submit_button("Ask", width="stretch")
            clr = c2.form_submit_button(":material/delete:", width="stretch")
        if clr:
            st.session_state.qa_history = []
            st.rerun()
        if ask and q.strip():
            prompt = (f"You are a clinical informatics advisor for MetroHealth Alliance, "
                      f"a {HEALTH_SYSTEM['hospitals']}-hospital, {HEALTH_SYSTEM['revenue']} health system with "
                      f"{HEALTH_SYSTEM['providers']} providers. Answer this CMIO question concisely (3-5 sentences). "
                      f"Be data-driven and action-oriented. Question: {q}")
            with st.spinner("Thinking..."):
                res = call_cortex(prompt)
            if not res.empty:
                st.session_state.qa_history.append({"q": q, "a": res.iloc[0]["SUMMARY"]})
                st.rerun()

    st.divider()
    fd = (today - data_max).days
    hc = "green" if fd <= 2 else ("orange" if fd <= 7 else "red")
    st.markdown(f"**Data Freshness:** :{hc}[{'Live' if fd<=2 else 'Delayed' if fd<=7 else 'Stale'}] ({fd}d)")
    st.caption("11 tables • 65K+ rows")


# ── Filter strings ───────────────────────────────────────────────────────────
ds = date_range[0].strftime("%Y-%m-%d") if len(date_range) == 2 else default_start.strftime("%Y-%m-%d")
de = date_range[1].strftime("%Y-%m-%d") if len(date_range) == 2 else default_end.strftime("%Y-%m-%d")
fac_f = f"AND FACILITY_ID IN ({','.join(repr(f) for f in sel_fac)})" if sel_fac else ""
dept_f = f"AND DEPARTMENT_ID IN ({','.join(repr(d) for d in sel_dept)})" if sel_dept else ""


# ── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    ":material/favorite: Clinical Quality & Outcomes",
    ":material/payments: Payer & Claims Intelligence",
    ":material/groups: SDOH & Population Health",
    ":material/auto_awesome: AI & Technology ROI",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — CLINICAL QUALITY & OUTCOMES
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    qkpi = run_query(f"""
        SELECT
            ROUND(AVG(READMISSION_RATE)*100, 1) AS READMIT,
            ROUND(AVG(HAI_RATE)*10000, 2) AS HAI,
            ROUND(AVG(HCAHPS_SCORE), 0) AS HCAHPS,
            ROUND(AVG(DOC_COMPLETION_RATE)*100, 1) AS DOC_COMP,
            ROUND(AVG(CDS_OVERRIDE_RATE)*100, 1) AS CDS_OVERRIDE,
            ROUND(AVG(ORDER_SET_COMPLIANCE)*100, 1) AS ORDER_SET
        FROM {SCHEMA}.CLINICAL_OUTCOMES
        WHERE METRIC_MONTH >= '{ds}' AND METRIC_MONTH <= '{de}' {fac_f} {dept_f}
    """)

    burn_kpi = run_query(f"""
        SELECT ROUND(AVG(AFTER_HOURS_MINUTES), 1) AS PAJAMA,
               ROUND(SUM(CASE WHEN AI_ASSIST_USED THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS DAX_PCT
        FROM {SCHEMA}.EHR_DAILY_USAGE
        WHERE USAGE_DATE >= '{ds}' AND USAGE_DATE <= '{de}' {fac_f} {dept_f}
    """)

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    with c1: kpi_card("30-Day Readmit", safe(qkpi["READMIT"].iloc[0], ".1f", "%"), "-0.9% vs prior yr", "inverse")
    with c2: kpi_card("HCAHPS Score", safe(qkpi["HCAHPS"].iloc[0], ".0f", "/100"), "+1.4 pts")
    with c3: kpi_card("HAI Rate /10K", safe(qkpi["HAI"].iloc[0], ".2f"), "-0.12", "inverse")
    with c4: kpi_card("Doc Completion", safe(qkpi["DOC_COMP"].iloc[0], ".1f", "%"), "+2.1%")
    with c5: kpi_card("Pajama Time", safe(burn_kpi["PAJAMA"].iloc[0], ".1f", " min"), "-3.2 min", "inverse")
    with c6: kpi_card("DAX Adoption", safe(burn_kpi["DAX_PCT"].iloc[0], ".1f", "%"), "+12.4%")

    section_header("📊", "Quality Performance Gauges")
    g1,g2,g3,g4 = st.columns(4)
    rv = qkpi["READMIT"].iloc[0] if not qkpi.empty else 0
    with g1: st.plotly_chart(gauge_chart(max(0, 100 - float(rv or 0)*5), "Readmit Score", 75, "#2563EB"), width="stretch")
    with g2: st.plotly_chart(gauge_chart(float(qkpi["HCAHPS"].iloc[0] or 0), "HCAHPS", 80, "#059669"), width="stretch")
    with g3: st.plotly_chart(gauge_chart(float(qkpi["DOC_COMP"].iloc[0] or 0), "Doc Completion", 90, "#7C3AED"), width="stretch")
    with g4: st.plotly_chart(gauge_chart(max(0, 100 - float(qkpi["CDS_OVERRIDE"].iloc[0] or 0)), "CDS Compliance", 60, "#D97706"), width="stretch")

    section_header("📈", "Monthly Trends")
    co1, co2 = st.columns(2)
    with co1:
        st.markdown("**30-Day Readmission Rate Trend**")
        trend = run_query(f"""
            SELECT METRIC_MONTH,
                   ROUND(AVG(READMISSION_RATE)*100, 2) AS READMIT,
                   ROUND(AVG(DOC_COMPLETION_RATE)*100, 1) AS DOC_COMP
            FROM {SCHEMA}.CLINICAL_OUTCOMES
            WHERE METRIC_MONTH >= '{ds}' AND METRIC_MONTH <= '{de}' {fac_f} {dept_f}
            GROUP BY METRIC_MONTH ORDER BY METRIC_MONTH
        """)
        if not trend.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=trend["METRIC_MONTH"], y=trend["READMIT"], name="Readmission %",
                          fill="tozeroy", fillcolor="rgba(220,38,38,0.08)", line=dict(color="#DC2626", width=2.5), mode="lines+markers", marker=dict(size=5)))
            fig.add_hline(y=15, line_dash="dot", line_color="#94A3B8", annotation_text="CMS Target: 15%", annotation_font_color="#94A3B8")
            fig.add_shape(type="line", x0=AI_ROLLOUT_DATE, x1=AI_ROLLOUT_DATE, y0=0, y1=1, yref="paper", line=dict(color="#059669", width=1.5, dash="dash"))
            fig.add_annotation(x=AI_ROLLOUT_DATE, y=0.95, yref="paper", text="DAX Rollout", showarrow=False, font=dict(color="#059669", size=10))
            st.plotly_chart(chart_defaults(fig, 320), width="stretch")

    with co2:
        st.markdown("**Provider After-Hours (Pajama Time) Trend**")
        pajama_trend = run_query(f"""
            SELECT DATE_TRUNC('month', USAGE_DATE) AS MO,
                   ROUND(AVG(AFTER_HOURS_MINUTES), 1) AS PAJAMA,
                   ROUND(AVG(INBASKET_AFTER_HOURS_MIN), 1) AS INBOX
            FROM {SCHEMA}.EHR_DAILY_USAGE
            WHERE USAGE_DATE >= '{ds}' AND USAGE_DATE <= '{de}' {fac_f} {dept_f}
            GROUP BY MO ORDER BY MO
        """)
        if not pajama_trend.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=pajama_trend["MO"], y=pajama_trend["PAJAMA"], name="Total After-Hours",
                          fill="tozeroy", fillcolor="rgba(37,99,235,0.08)", line=dict(color="#2563EB", width=2.5), mode="lines+markers", marker=dict(size=5)))
            fig.add_trace(go.Scatter(x=pajama_trend["MO"], y=pajama_trend["INBOX"], name="InBasket", line=dict(color="#D97706", width=1.5, dash="dash")))
            fig.add_shape(type="line", x0=AI_ROLLOUT_DATE, x1=AI_ROLLOUT_DATE, y0=0, y1=1, yref="paper", line=dict(color="#059669", width=1.5, dash="dash"))
            fig.add_annotation(x=AI_ROLLOUT_DATE, y=0.95, yref="paper", text="DAX Rollout", showarrow=False, font=dict(color="#059669", size=10))
            fig = chart_defaults(fig, 320)
            fig.update_layout(yaxis_title="Minutes / Day")
            st.plotly_chart(fig, width="stretch")

    section_header("🏥", "Department Scorecard")
    corr = run_query(f"""
        SELECT o.DEPARTMENT_NAME,
               ROUND(AVG(o.DOC_COMPLETION_RATE)*100, 1) AS DOC_COMP,
               ROUND(AVG(o.READMISSION_RATE)*100, 1) AS READMIT,
               ROUND(AVG(o.CDS_OVERRIDE_RATE)*100, 1) AS CDS_OVERRIDE,
               ROUND(AVG(o.HCAHPS_SCORE), 0) AS HCAHPS,
               SUM(o.ENCOUNTER_COUNT) AS ENCOUNTERS
        FROM {SCHEMA}.CLINICAL_OUTCOMES o
        WHERE o.METRIC_MONTH >= '{ds}' AND o.METRIC_MONTH <= '{de}' {fac_f} {dept_f}
        GROUP BY o.DEPARTMENT_NAME ORDER BY READMIT DESC
    """)
    if not corr.empty:
        co1, co2 = st.columns(2)
        with co1:
            st.markdown("**Doc Completion vs Readmission Rate**")
            fig = px.scatter(corr, x="DOC_COMP", y="READMIT", size="ENCOUNTERS", text="DEPARTMENT_NAME",
                             color="READMIT", color_continuous_scale=["#059669","#D97706","#DC2626"],
                             labels={"DOC_COMP": "Doc Completion %", "READMIT": "Readmission %"})
            fig.update_traces(textposition="top center", textfont_size=9)
            st.plotly_chart(chart_defaults(fig, 340), width="stretch")
        with co2:
            st.markdown("**Quality Metrics Heatmap by Department**")
            hm = corr.set_index("DEPARTMENT_NAME")[["READMIT","CDS_OVERRIDE","DOC_COMP","HCAHPS"]]
            fig = px.imshow(hm.T, color_continuous_scale=["#059669","#FDE68A","#DC2626"],
                            labels=dict(x="Department", y="Metric", color="Value"), aspect="auto")
            st.plotly_chart(chart_defaults(fig, 340), width="stretch")

    with st.expander(":material/code: View SQL"):
        st.code(f"""SELECT DEPARTMENT_NAME, AVG(DOC_COMPLETION_RATE)*100 AS doc_comp,
       AVG(READMISSION_RATE)*100 AS readmit, AVG(CDS_OVERRIDE_RATE)*100 AS cds_override
FROM {SCHEMA}.CLINICAL_OUTCOMES WHERE METRIC_MONTH BETWEEN '{ds}' AND '{de}'
GROUP BY DEPARTMENT_NAME;""", language="sql")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PAYER & CLAIMS INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    claims_kpi = run_query(f"""
        SELECT
            COUNT(*) AS TOTAL_CLAIMS,
            ROUND(SUM(BILLED_AMOUNT), 0) AS TOTAL_BILLED,
            ROUND(SUM(PAID_AMOUNT), 0) AS TOTAL_PAID,
            ROUND(SUM(CASE WHEN CLAIM_STATUS='Denied' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0), 1) AS DENIAL_RATE,
            ROUND(SUM(CASE WHEN CLAIM_STATUS='Denied' THEN BILLED_AMOUNT ELSE 0 END), 0) AS DENIED_AMOUNT,
            ROUND(AVG(DAYS_TO_PAYMENT), 0) AS AVG_DAYS_PAY,
            ROUND(SUM(CASE WHEN APPEAL_WON THEN 1 ELSE 0 END)*100.0/NULLIF(SUM(CASE WHEN APPEAL_SUBMITTED THEN 1 ELSE 0 END),0), 1) AS APPEAL_WIN_RATE
        FROM {SCHEMA}.PAYER_CLAIMS
        WHERE CLAIM_DATE >= '{ds}' AND CLAIM_DATE <= '{de}' {fac_f}
    """)

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: kpi_card("Total Claims", f"{int(claims_kpi['TOTAL_CLAIMS'].iloc[0] or 0):,}")
    with c2: kpi_card("Revenue Collected", f"${int(claims_kpi['TOTAL_PAID'].iloc[0] or 0):,.0f}", f"of ${int(claims_kpi['TOTAL_BILLED'].iloc[0] or 0):,.0f} billed")
    with c3: kpi_card("Denial Rate", safe(claims_kpi["DENIAL_RATE"].iloc[0], ".1f", "%"), "Target < 8%", "inverse")
    with c4: kpi_card("Denied Revenue", f"${int(claims_kpi['DENIED_AMOUNT'].iloc[0] or 0):,.0f}", delta_color="off")
    with c5: kpi_card("Appeal Win Rate", safe(claims_kpi["APPEAL_WIN_RATE"].iloc[0], ".1f", "%"), "+5.2%")

    section_header("💰", "Revenue Waterfall")
    st.markdown("**Billed → Collected Revenue Flow**")
    billed = float(claims_kpi["TOTAL_BILLED"].iloc[0] or 0)
    paid = float(claims_kpi["TOTAL_PAID"].iloc[0] or 0)
    denied = float(claims_kpi["DENIED_AMOUNT"].iloc[0] or 0)
    fig = go.Figure(go.Waterfall(
        x=["Billed", "Contractual Adj.", "Denials", "Collected"],
        y=[billed, -(billed - paid - denied), -denied, 0],
        measure=["absolute", "relative", "relative", "total"],
        connector={"line": {"color": "#E2E8F0"}},
        decreasing={"marker": {"color": "#FCA5A5"}},
        increasing={"marker": {"color": "#86EFAC"}},
        totals={"marker": {"color": "#2563EB"}}
    ))
    fig = chart_defaults(fig, 320)
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width="stretch")

    section_header("📋", "Denial Analysis")
    co1, co2 = st.columns(2)
    with co1:
        st.markdown("**Denial Rate by Payer**")
        by_payer = run_query(f"""
            SELECT PAYER_NAME, PAYER_TYPE,
                   COUNT(*) AS CLAIMS,
                   ROUND(SUM(CASE WHEN CLAIM_STATUS='Denied' THEN 1 ELSE 0 END)*100.0/COUNT(*), 1) AS DENIAL_RATE,
                   ROUND(SUM(BILLED_AMOUNT), 0) AS BILLED,
                   ROUND(SUM(PAID_AMOUNT), 0) AS PAID
            FROM {SCHEMA}.PAYER_CLAIMS
            WHERE CLAIM_DATE >= '{ds}' AND CLAIM_DATE <= '{de}' {fac_f}
            GROUP BY PAYER_NAME, PAYER_TYPE ORDER BY DENIAL_RATE DESC
        """)
        if not by_payer.empty:
            fig = px.bar(by_payer, x="PAYER_NAME", y="DENIAL_RATE", color="PAYER_TYPE",
                         color_discrete_map={"Government": "#2563EB", "Commercial": "#7C3AED", "Self-Pay": "#D97706"},
                         text="DENIAL_RATE", labels={"PAYER_NAME": "", "DENIAL_RATE": "Denial Rate %"})
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig.add_hline(y=8, line_dash="dot", line_color="#DC2626", annotation_text="8% Target")
            st.plotly_chart(chart_defaults(fig, 340), width="stretch")

    with co2:
        st.markdown("**Top Denial Codes by Volume (Treemap)**")
        by_code = run_query(f"""
            SELECT DENIAL_CODE, DENIAL_REASON, COUNT(*) AS CNT,
                   ROUND(SUM(BILLED_AMOUNT), 0) AS LOST_REVENUE
            FROM {SCHEMA}.PAYER_CLAIMS
            WHERE CLAIM_STATUS = 'Denied' AND CLAIM_DATE >= '{ds}' AND CLAIM_DATE <= '{de}' {fac_f}
            GROUP BY DENIAL_CODE, DENIAL_REASON ORDER BY CNT DESC LIMIT 8
        """)
        if not by_code.empty:
            fig = px.treemap(by_code, path=["DENIAL_CODE"], values="CNT", color="LOST_REVENUE",
                             color_continuous_scale=["#DBEAFE","#2563EB","#1E3A5F"],
                             hover_data=["DENIAL_REASON","LOST_REVENUE"],
                             labels={"CNT": "Claims", "LOST_REVENUE": "Lost Revenue"})
            fig.update_layout(height=340, margin=dict(l=5,r=5,t=30,b=5))
            st.plotly_chart(fig, width="stretch")

    section_header("📅", "Monthly Claims Trend")
    st.markdown("**Revenue Collected vs Denial Rate — Monthly**")
    monthly = run_query(f"""
        SELECT DATE_TRUNC('month', CLAIM_DATE) AS MO,
               COUNT(*) AS CLAIMS,
               ROUND(SUM(CASE WHEN CLAIM_STATUS='Denied' THEN 1 ELSE 0 END)*100.0/COUNT(*), 1) AS DENIAL_RATE,
               ROUND(SUM(PAID_AMOUNT), 0) AS REVENUE
        FROM {SCHEMA}.PAYER_CLAIMS
        WHERE CLAIM_DATE >= '{ds}' AND CLAIM_DATE <= '{de}' {fac_f}
        GROUP BY MO ORDER BY MO
    """)
    if not monthly.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=monthly["MO"], y=monthly["REVENUE"], name="Revenue Collected",
                     marker_color="#2563EB", opacity=0.7, yaxis="y"))
        fig.add_trace(go.Scatter(x=monthly["MO"], y=monthly["DENIAL_RATE"], name="Denial Rate %",
                     line=dict(color="#DC2626", width=2.5), mode="lines+markers", marker=dict(size=6), yaxis="y2"))
        chart_defaults(fig, 320)
        fig.update_layout(yaxis=dict(title="Revenue ($)", side="left"),
                          yaxis2=dict(title="Denial Rate %", side="right", overlaying="y", range=[0, 25]),
                          barmode="group")
        st.plotly_chart(fig, width="stretch")

    section_header("🔍", "Service Line Performance")
    by_sl = run_query(f"""
        SELECT SERVICE_LINE,
               COUNT(*) AS CLAIMS,
               ROUND(SUM(CASE WHEN CLAIM_STATUS='Denied' THEN 1 ELSE 0 END)*100.0/COUNT(*), 1) AS DENIAL_RATE,
               ROUND(SUM(PAID_AMOUNT), 0) AS REVENUE,
               ROUND(AVG(DAYS_TO_PAYMENT), 0) AS AVG_DAYS
        FROM {SCHEMA}.PAYER_CLAIMS
        WHERE CLAIM_DATE >= '{ds}' AND CLAIM_DATE <= '{de}' {fac_f}
        GROUP BY SERVICE_LINE ORDER BY REVENUE DESC
    """)
    if not by_sl.empty:
        def hl_denial(row):
            v = row.get("DENIAL_RATE", 0)
            if v > 15: return ["background-color:#FEE2E2"] * len(row)
            if v > 10: return ["background-color:#FEF9C3"] * len(row)
            return [""] * len(row)
        st.dataframe(by_sl.style.apply(hl_denial, axis=1), width="stretch", hide_index=True,
                     column_config={"REVENUE": st.column_config.NumberColumn("Revenue", format="$%d"),
                                    "DENIAL_RATE": st.column_config.ProgressColumn("Denial %", min_value=0, max_value=30),
                                    "AVG_DAYS": st.column_config.NumberColumn("Avg Days to Pay", format="%d")})

    with st.expander(":material/code: View SQL"):
        st.code(f"""SELECT PAYER_NAME, COUNT(*) AS claims,
       SUM(CASE WHEN CLAIM_STATUS='Denied' THEN 1 ELSE 0 END)*100.0/COUNT(*) AS denial_rate,
       SUM(BILLED_AMOUNT) AS billed, SUM(PAID_AMOUNT) AS paid
FROM {SCHEMA}.PAYER_CLAIMS WHERE CLAIM_DATE BETWEEN '{ds}' AND '{de}'
GROUP BY PAYER_NAME ORDER BY denial_rate DESC;""", language="sql")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SDOH & POPULATION HEALTH
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    sdoh_kpi = run_query(f"""
        SELECT
            COUNT(DISTINCT ZIP_CODE) AS COMMUNITIES,
            ROUND(AVG(COMPOSITE_SDOH_SCORE), 0) AS AVG_SDOH_SCORE,
            ROUND(AVG(UNINSURED_PCT), 1) AS AVG_UNINSURED,
            ROUND(AVG(CARE_GAP_CLOSURE_PCT), 1) AS AVG_CARE_GAP,
            ROUND(AVG(ED_VISIT_RATE_PER_1K), 1) AS AVG_ED_RATE,
            SUM(CASE WHEN SDOH_RISK_TIER='High' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0) AS HIGH_RISK_PCT
        FROM {SCHEMA}.SDOH_POPULATION
        WHERE METRIC_MONTH >= '{ds}' AND METRIC_MONTH <= '{de}'
    """)

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: kpi_card("Communities Tracked", safe(sdoh_kpi["COMMUNITIES"].iloc[0], ".0f"))
    with c2: kpi_card("Avg SDOH Risk Score", safe(sdoh_kpi["AVG_SDOH_SCORE"].iloc[0], ".0f", "/100"))
    with c3: kpi_card("Avg Uninsured", safe(sdoh_kpi["AVG_UNINSURED"].iloc[0], ".1f", "%"))
    with c4: kpi_card("Care Gap Closure", safe(sdoh_kpi["AVG_CARE_GAP"].iloc[0], ".1f", "%"), "Target > 80%")
    with c5: kpi_card("Avg ED Rate /1K", safe(sdoh_kpi["AVG_ED_RATE"].iloc[0], ".1f"))

    section_header("🗺️", "Community Risk Map")
    community = run_query(f"""
        SELECT COMMUNITY_NAME, ZIP_CODE, SDOH_RISK_TIER,
               ROUND(AVG(COMPOSITE_SDOH_SCORE), 0) AS RISK_SCORE,
               ROUND(AVG(UNINSURED_PCT), 1) AS UNINSURED,
               ROUND(AVG(MEDIAN_INCOME), 0) AS INCOME,
               ROUND(AVG(ED_VISIT_RATE_PER_1K), 1) AS ED_RATE,
               ROUND(AVG(CARE_GAP_CLOSURE_PCT), 1) AS CARE_GAP
        FROM {SCHEMA}.SDOH_POPULATION
        WHERE METRIC_MONTH >= '{ds}' AND METRIC_MONTH <= '{de}'
        GROUP BY COMMUNITY_NAME, ZIP_CODE, SDOH_RISK_TIER
        ORDER BY RISK_SCORE DESC
    """)
    co1, co2 = st.columns(2)
    with co1:
        st.markdown("**Income vs ED Utilization by Community**")
        if not community.empty:
            fig = px.scatter(community, x="INCOME", y="ED_RATE", size="RISK_SCORE",
                             color="SDOH_RISK_TIER", text="COMMUNITY_NAME",
                             color_discrete_map={"High": "#DC2626", "Medium": "#D97706", "Low": "#059669"},
                             labels={"INCOME": "Median Income ($)", "ED_RATE": "ED Visits /1K"})
            fig.update_traces(textposition="top center", textfont_size=9)
            st.plotly_chart(chart_defaults(fig, 360), width="stretch")

    with co2:
        st.markdown("**SDOH Risk Distribution by Community**")
        if not community.empty:
            fig = px.sunburst(community, path=["SDOH_RISK_TIER", "COMMUNITY_NAME"], values="RISK_SCORE",
                              color="RISK_SCORE", color_continuous_scale=["#DCFCE7","#FDE68A","#FCA5A5"],
                              labels={"RISK_SCORE": "SDOH Score"})
            fig.update_layout(height=360, margin=dict(l=5,r=5,t=30,b=5))
            st.plotly_chart(fig, width="stretch")

    section_header("📊", "Social Determinants Breakdown")
    co1, co2 = st.columns(2)
    with co1:
        st.markdown("**Barrier Prevalence by Community**")
        barriers = run_query(f"""
            SELECT COMMUNITY_NAME,
                   ROUND(AVG(HOUSING_INSTABILITY_PCT), 1) AS HOUSING,
                   ROUND(AVG(TRANSPORT_BARRIER_PCT), 1) AS TRANSPORT,
                   ROUND(AVG(LANGUAGE_BARRIER_PCT), 1) AS LANGUAGE,
                   ROUND(AVG(UNINSURED_PCT), 1) AS UNINSURED
            FROM {SCHEMA}.SDOH_POPULATION
            WHERE METRIC_MONTH >= '{ds}' AND METRIC_MONTH <= '{de}'
            GROUP BY COMMUNITY_NAME ORDER BY HOUSING DESC
        """)
        if not barriers.empty:
            fig = go.Figure()
            for col, color, name in [("HOUSING","#DC2626","Housing"), ("TRANSPORT","#D97706","Transport"),
                                      ("LANGUAGE","#7C3AED","Language"), ("UNINSURED","#2563EB","Uninsured")]:
                fig.add_trace(go.Bar(name=name, x=barriers["COMMUNITY_NAME"], y=barriers[col], marker_color=color))
            chart_defaults(fig, 360)
            fig.update_layout(barmode="group", xaxis_tickangle=-35)
            st.plotly_chart(fig, width="stretch")

    with co2:
        st.markdown("**Chronic Condition Prevalence by SDOH Risk Tier**")
        conditions = run_query(f"""
            SELECT CHRONIC_CONDITION, SDOH_RISK_TIER,
                   ROUND(AVG(PREVALENCE_PCT), 1) AS PREVALENCE,
                   ROUND(AVG(READMISSION_RATE_PCT), 1) AS READMIT
            FROM {SCHEMA}.SDOH_POPULATION
            WHERE METRIC_MONTH >= '{ds}' AND METRIC_MONTH <= '{de}'
            GROUP BY CHRONIC_CONDITION, SDOH_RISK_TIER
            ORDER BY CHRONIC_CONDITION, SDOH_RISK_TIER
        """)
        if not conditions.empty:
            fig = px.bar(conditions, x="CHRONIC_CONDITION", y="PREVALENCE", color="SDOH_RISK_TIER",
                         barmode="group",
                         color_discrete_map={"High": "#DC2626", "Medium": "#D97706", "Low": "#059669"},
                         labels={"CHRONIC_CONDITION": "", "PREVALENCE": "Prevalence %"})
            st.plotly_chart(chart_defaults(fig, 360), width="stretch")

    section_header("📋", "Community Detail")
    detail = run_query(f"""
        SELECT COMMUNITY_NAME, ZIP_CODE, SDOH_RISK_TIER,
               ROUND(AVG(COMPOSITE_SDOH_SCORE), 0) AS SDOH_SCORE,
               ROUND(AVG(MEDIAN_INCOME), 0) AS MEDIAN_INCOME,
               ROUND(AVG(UNINSURED_PCT), 1) AS UNINSURED_PCT,
               ROUND(AVG(HEALTH_LITERACY_SCORE), 0) AS HEALTH_LITERACY,
               ROUND(AVG(ED_VISIT_RATE_PER_1K), 1) AS ED_RATE,
               ROUND(AVG(CARE_GAP_CLOSURE_PCT), 1) AS CARE_GAP_PCT,
               ROUND(AVG(PREVENTIVE_SCREENING_PCT), 1) AS SCREENING_PCT
        FROM {SCHEMA}.SDOH_POPULATION
        WHERE METRIC_MONTH >= '{ds}' AND METRIC_MONTH <= '{de}'
        GROUP BY COMMUNITY_NAME, ZIP_CODE, SDOH_RISK_TIER
        ORDER BY SDOH_SCORE DESC
    """)
    if not detail.empty:
        def hl_risk(row):
            t = row.get("SDOH_RISK_TIER", "")
            if t == "High": return ["background-color:#FEE2E2"] * len(row)
            if t == "Medium": return ["background-color:#FEF9C3"] * len(row)
            return ["background-color:#DCFCE7"] * len(row)
        st.dataframe(detail.style.apply(hl_risk, axis=1), width="stretch", hide_index=True,
                     column_config={"SDOH_SCORE": st.column_config.ProgressColumn("SDOH Score", min_value=0, max_value=100),
                                    "CARE_GAP_PCT": st.column_config.ProgressColumn("Care Gap %", min_value=0, max_value=100),
                                    "MEDIAN_INCOME": st.column_config.NumberColumn("Income", format="$%d"),
                                    "HEALTH_LITERACY": st.column_config.ProgressColumn("Health Lit.", min_value=0, max_value=100)})

    with st.expander(":material/code: View SQL"):
        st.code(f"""SELECT COMMUNITY_NAME, ZIP_CODE, SDOH_RISK_TIER,
       AVG(COMPOSITE_SDOH_SCORE) AS sdoh_score, AVG(MEDIAN_INCOME) AS income,
       AVG(ED_VISIT_RATE_PER_1K) AS ed_rate, AVG(CARE_GAP_CLOSURE_PCT) AS care_gap
FROM {SCHEMA}.SDOH_POPULATION WHERE METRIC_MONTH BETWEEN '{ds}' AND '{de}'
GROUP BY COMMUNITY_NAME, ZIP_CODE, SDOH_RISK_TIER ORDER BY sdoh_score DESC;""", language="sql")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — AI & TECHNOLOGY ROI
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    ai_kpi = run_query(f"""
        WITH u AS (
            SELECT
                SUM(CASE WHEN AI_ASSIST_USED THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0) AS AI_RATE,
                AVG(CASE WHEN AI_ASSIST_USED THEN AFTER_HOURS_MINUTES END) AS PAJAMA_AI,
                AVG(CASE WHEN NOT AI_ASSIST_USED THEN AFTER_HOURS_MINUTES END) AS PAJAMA_NO_AI,
                AVG(CASE WHEN AI_ASSIST_USED THEN NOTE_CLOSURE_AFTER_HOURS_MIN END) AS NOTE_AI,
                AVG(CASE WHEN NOT AI_ASSIST_USED THEN NOTE_CLOSURE_AFTER_HOURS_MIN END) AS NOTE_NO_AI
            FROM {SCHEMA}.EHR_DAILY_USAGE
            WHERE USAGE_DATE >= '{ds}' AND USAGE_DATE <= '{de}' {fac_f} {dept_f}
        )
        SELECT ROUND(AI_RATE, 1) AS AI_PCT,
               ROUND(PAJAMA_AI, 1) AS WITH_AI,
               ROUND(PAJAMA_NO_AI, 1) AS WITHOUT_AI,
               ROUND(PAJAMA_NO_AI - PAJAMA_AI, 1) AS DELTA,
               ROUND(NOTE_NO_AI - NOTE_AI, 1) AS NOTE_DELTA
        FROM u
    """)

    train_pct = run_query(f"""
        SELECT ROUND(SUM(CASE WHEN STATUS='Completed' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS PCT
        FROM {SCHEMA}.TRAINING_LMS WHERE COURSE_CATEGORY IN ('AI/ML','EHR Optimization') {fac_f} {dept_f}
    """)

    tickets = run_query(f"""
        SELECT COUNT(*) AS OPEN_TICKETS FROM {SCHEMA}.SUPPORT_TICKETS
        WHERE STATUS IN ('Open','In Progress') {fac_f} {dept_f}
    """)

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: kpi_card("DAX Adoption", safe(ai_kpi["AI_PCT"].iloc[0], ".1f", "%"), "+12.4%")
    with c2: kpi_card("Time Saved /Day", safe(ai_kpi["DELTA"].iloc[0], ".1f", " min"), "per provider", "off")
    with c3: kpi_card("With AI", safe(ai_kpi["WITH_AI"].iloc[0], ".1f", " min"), "after-hours", "off")
    with c4: kpi_card("AI Training Done", safe(train_pct["PCT"].iloc[0], ".1f", "%"), "+8.2%")
    with c5: kpi_card("Open IT Tickets", safe(tickets["OPEN_TICKETS"].iloc[0], ".0f"), delta_color="off")

    section_header("🤖", "AI Impact Analysis")
    co1, co2 = st.columns(2)
    with co1:
        st.markdown("**After-Hours Minutes: With vs Without DAX**")
        by_dept = run_query(f"""
            SELECT DEPARTMENT_NAME,
                   ROUND(AVG(CASE WHEN AI_ASSIST_USED THEN AFTER_HOURS_MINUTES END), 1) AS WITH_AI,
                   ROUND(AVG(CASE WHEN NOT AI_ASSIST_USED THEN AFTER_HOURS_MINUTES END), 1) AS WITHOUT_AI
            FROM {SCHEMA}.EHR_DAILY_USAGE
            WHERE USAGE_DATE >= '{ds}' AND USAGE_DATE <= '{de}' {fac_f} {dept_f}
            GROUP BY DEPARTMENT_NAME ORDER BY WITHOUT_AI DESC
        """)
        if not by_dept.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Without AI", x=by_dept["DEPARTMENT_NAME"], y=by_dept["WITHOUT_AI"],
                         marker_color="#94A3B8"))
            fig.add_trace(go.Bar(name="With AI (DAX)", x=by_dept["DEPARTMENT_NAME"], y=by_dept["WITH_AI"],
                         marker_color="#2563EB"))
            chart_defaults(fig, 360)
            fig.update_layout(barmode="group", xaxis_tickangle=-35, yaxis_title="After-Hours Min/Day")
            st.plotly_chart(fig, width="stretch")

    with co2:
        st.markdown("**DAX Adoption Rate Over Time**")
        adoption_trend = run_query(f"""
            SELECT DATE_TRUNC('month', USAGE_DATE) AS MO,
                   ROUND(SUM(CASE WHEN AI_ASSIST_USED THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0), 1) AS AI_PCT
            FROM {SCHEMA}.EHR_DAILY_USAGE
            WHERE USAGE_DATE >= '{ds}' AND USAGE_DATE <= '{de}' {fac_f} {dept_f}
            GROUP BY MO ORDER BY MO
        """)
        if not adoption_trend.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=adoption_trend["MO"], y=adoption_trend["AI_PCT"],
                          fill="tozeroy", fillcolor="rgba(37,99,235,0.12)", line=dict(color="#2563EB", width=3),
                          mode="lines+markers", marker=dict(size=6)))
            fig.add_shape(type="line", x0=AI_ROLLOUT_DATE, x1=AI_ROLLOUT_DATE, y0=0, y1=1, yref="paper",
                          line=dict(color="#059669", width=2, dash="dash"))
            fig.add_annotation(x=AI_ROLLOUT_DATE, y=0.95, yref="paper", text="DAX Launch", showarrow=False,
                               font=dict(color="#059669", size=10))
            chart_defaults(fig, 360)
            fig.update_layout(yaxis_title="DAX Adoption %")
            st.plotly_chart(fig, width="stretch")

    section_header("💡", "ROI Calculator")
    delta_val = float(ai_kpi["DELTA"].iloc[0] or 0)
    adoption_pct = float(ai_kpi["AI_PCT"].iloc[0] or 0)
    providers_using = int(HEALTH_SYSTEM["providers"] * adoption_pct / 100)
    annual_hours_saved = providers_using * delta_val * 250 / 60
    physician_value = annual_hours_saved * 180

    rc1, rc2, rc3, rc4 = st.columns(4)
    with rc1: kpi_card("Providers Using DAX", f"{providers_using}")
    with rc2: kpi_card("Annual Hours Saved", f"{annual_hours_saved:,.0f} hrs")
    with rc3: kpi_card("Physician Time Value", f"${physician_value:,.0f}", "@ $180/hr", "off")
    with rc4: kpi_card("Investment ROI", f"{physician_value/2100000*100:.0f}%" if physician_value > 0 else "--", "on $2.1M investment")

    section_header("🧠", "AI Executive Briefing", "Powered by Snowflake Cortex")
    if OFFLINE_MODE:
        st.info("AI Briefing requires live Snowflake connection.", icon=":material/cloud_off:")
    else:
        if st.button("Generate AI Executive Summary", type="primary", width="stretch"):
            with st.spinner("Cortex AI is analyzing your data..."):
                metrics = run_query(f"""
                    WITH q AS (SELECT ROUND(AVG(READMISSION_RATE)*100,1) AS readmit, ROUND(AVG(HCAHPS_SCORE),0) AS hcahps,
                               ROUND(AVG(DOC_COMPLETION_RATE)*100,1) AS doc_comp FROM {SCHEMA}.CLINICAL_OUTCOMES
                               WHERE METRIC_MONTH >= DATEADD(month,-1,CURRENT_DATE())),
                    p AS (SELECT ROUND(AVG(AFTER_HOURS_MINUTES),1) AS pajama,
                               ROUND(SUM(CASE WHEN AI_ASSIST_USED THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS dax
                          FROM {SCHEMA}.EHR_DAILY_USAGE WHERE USAGE_DATE >= DATEADD(month,-1,CURRENT_DATE())),
                    c AS (SELECT ROUND(SUM(CASE WHEN CLAIM_STATUS='Denied' THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS denial_rate
                          FROM {SCHEMA}.PAYER_CLAIMS WHERE CLAIM_DATE >= DATEADD(month,-1,CURRENT_DATE()))
                    SELECT q.*, p.*, c.* FROM q, p, c
                """)
                if not metrics.empty:
                    m = metrics.iloc[0]
                    prompt = (f"You are the AI advisor for the CMIO at MetroHealth Alliance ({HEALTH_SYSTEM['hospitals']} hospitals, "
                              f"{HEALTH_SYSTEM['providers']} providers, {HEALTH_SYSTEM['revenue']} revenue). "
                              f"Current metrics: Readmission rate {m.get('READMIT','N/A')}%, HCAHPS {m.get('HCAHPS','N/A')}, "
                              f"Doc completion {m.get('DOC_COMP','N/A')}%, Pajama time {m.get('PAJAMA','N/A')} min/day, "
                              f"DAX adoption {m.get('DAX','N/A')}%, Claims denial rate {m.get('DENIAL_RATE','N/A')}%. "
                              f"Write a structured executive summary: 1) System Performance (2-3 sentences), "
                              f"2) Areas of Concern (bullets with specific recommendations), "
                              f"3) Priority Actions for CMIO (3-5 items for next 30 days), "
                              f"4) Board Talking Points (2-3 key messages). Be data-driven and action-oriented.")
                    res = call_cortex(prompt)
                    if not res.empty:
                        st.markdown(
                            f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-left:4px solid #2563EB;'
                            f'padding:20px;border-radius:8px;line-height:1.8;font-size:13px;">'
                            + res.iloc[0]["SUMMARY"].replace("\n", "<br>") + "</div>",
                            unsafe_allow_html=True)

    with st.expander(":material/code: View SQL"):
        st.code(f"""-- AI ROI: DAX vs non-DAX after-hours comparison
SELECT DEPARTMENT_NAME,
       AVG(CASE WHEN AI_ASSIST_USED THEN AFTER_HOURS_MINUTES END) AS with_ai,
       AVG(CASE WHEN NOT AI_ASSIST_USED THEN AFTER_HOURS_MINUTES END) AS without_ai
FROM {SCHEMA}.EHR_DAILY_USAGE GROUP BY DEPARTMENT_NAME;""", language="sql")


# ── Footer ───────────────────────────────────────────────────────────────────
st.divider()
fc1, fc2, fc3 = st.columns(3)
with fc1:
    st.markdown("**Data Architecture**")
    st.caption("11 tables • 65K+ rows • Epic + Workday + Claims + SDOH")
with fc2:
    st.markdown("**Key CMIO Metrics**")
    st.caption("Quality • Claims • SDOH • AI ROI • Burnout")
with fc3:
    st.markdown(f"**{HEALTH_SYSTEM['name']}**")
    st.caption(f"{HEALTH_SYSTEM['hospitals']} Hospitals • {HEALTH_SYSTEM['providers']} Providers • {HEALTH_SYSTEM['revenue']}")
