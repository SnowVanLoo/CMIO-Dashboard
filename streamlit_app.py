import streamlit as st
st.set_page_config(page_title="CMIO Command Center", layout="wide", page_icon=":material/monitor_heart:")
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from data_generator import (
    get_facilities_df, get_departments_df, get_ehr_usage,
    get_clinical_outcomes, get_payer_claims, get_sdoh_population,
    get_training_lms, get_support_tickets,
    AI_ROLLOUT_DATE, AI_ROLLOUT, START_DATE, END_DATE,
)

HEALTH_SYSTEM = {
    "name": "MetroHealth Alliance", "hospitals": 12, "clinics": 115,
    "revenue": "$3.8B", "providers": 220, "beds": 3730,
}
P = ["#2563EB","#059669","#D97706","#DC2626","#7C3AED","#0891B2","#EA580C","#65A30D"]


def safe(val, fmt=".1f", sfx="", fb="--"):
    try:
        if pd.isna(val): return fb
        return f"{val:{fmt}}{sfx}"
    except Exception: return fb


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
        mode="gauge+number", value=value,
        title={"text": title, "font": {"size": 13, "color": "#475569"}},
        number={"font": {"size": 28, "color": "#0F172A"}, "suffix": "%"},
        gauge={"axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "#E2E8F0"},
               "bar": {"color": color, "thickness": 0.7},
               "bgcolor": "#F1F5F9", "borderwidth": 0,
               "threshold": {"line": {"color": "#DC2626", "width": 2},
                              "thickness": 0.8, "value": target} if target else {},
               "steps": [{"range": [0, 40], "color": "#FEE2E2"},
                          {"range": [40, 70], "color": "#FEF9C3"},
                          {"range": [70, 100], "color": "#DCFCE7"}]}))
    fig.update_layout(height=height, margin=dict(l=20,r=20,t=40,b=10),
                      paper_bgcolor="rgba(0,0,0,0)", font={"color": "#475569"})
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
  <h1 style="color:white;margin:0;font-size:26px;font-weight:800;letter-spacing:-0.02em;">CMIO Command Center</h1>
  <p style="color:#93C5FD;margin:6px 0 0 0;font-size:13px;font-weight:500;">
    Clinical Informatics Intelligence &nbsp;&bull;&nbsp; MetroHealth Alliance
    &nbsp;&bull;&nbsp; Powered by Snowflake
  </p>
</div>
""", unsafe_allow_html=True)

# ── Load all data once ────────────────────────────────────────────────────────
_ehr    = get_ehr_usage()
_co     = get_clinical_outcomes()
_claims = get_payer_claims()
_sdoh   = get_sdoh_population()
_train  = get_training_lms()
_tickets= get_support_tickets()
_facs   = get_facilities_df()
_depts  = get_departments_df()

data_max = pd.Timestamp(END_DATE).date()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### {HEALTH_SYSTEM['name']}")
    st.caption(f"{HEALTH_SYSTEM['hospitals']} Hospitals • {HEALTH_SYSTEM['clinics']} Clinics • {HEALTH_SYSTEM['providers']} Providers • {HEALTH_SYSTEM['revenue']}")
    st.divider()

    today = datetime.now().date()
    default_end = data_max
    default_start = default_end - timedelta(days=365)
    date_range = st.date_input("Date Range", value=(default_start, default_end), key="dr")

    sel_fac = st.multiselect("Facilities", options=_facs["FACILITY_ID"].tolist(),
        format_func=lambda x: _facs.set_index("FACILITY_ID").loc[x, "FACILITY_NAME"],
        default=None, placeholder="All Facilities")

    sel_dept = st.multiselect("Departments", options=_depts["DEPARTMENT_ID"].tolist(),
        format_func=lambda x: _depts.set_index("DEPARTMENT_ID").loc[x, "DEPARTMENT_NAME"],
        default=None, placeholder="All Departments")

    st.divider()

    st.markdown("#### 💡 Quick Insights")
    with st.expander("Key talking points", expanded=False):
        st.markdown("""
- **Emergency Medicine** has the highest pajama time at ~54 min/day — a prime target for DAX rollout
- **DAX adoption** jumped from 8% to 44% post-Oct 2025 rollout, driving a 16 min/day reduction
- **Self-Pay claims** have a 28% denial rate — 3× the 8% target, representing ~$2.1M in lost revenue
- **Cedar Park (63107)** is the highest-risk SDOH community with a composite score of 78/100
- **Cardiology** shows the strongest EHR adoption improvement: 62→79 post-AI rollout
        """)

    st.divider()
    st.markdown("**Data Freshness:** :green[Live] (synthetic)")
    st.caption("11 tables • 65K+ rows • Zero compute cost")


# ── Filter data ───────────────────────────────────────────────────────────────
ds = date_range[0] if len(date_range) == 2 else default_start
de = date_range[1] if len(date_range) == 2 else default_end

def filter_ehr(df):
    d = df[(pd.to_datetime(df["USAGE_DATE"]).dt.date >= ds) & (pd.to_datetime(df["USAGE_DATE"]).dt.date <= de)]
    if sel_fac: d = d[d["FACILITY_ID"].isin(sel_fac)]
    if sel_dept: d = d[d["DEPARTMENT_ID"].isin(sel_dept)]
    return d

def filter_co(df):
    d = df[(pd.to_datetime(df["METRIC_MONTH"]).dt.date >= ds) & (pd.to_datetime(df["METRIC_MONTH"]).dt.date <= de)]
    if sel_fac: d = d[d["FACILITY_ID"].isin(sel_fac)]
    if sel_dept: d = d[d["DEPARTMENT_ID"].isin(sel_dept)]
    return d

def filter_claims(df):
    d = df[(pd.to_datetime(df["CLAIM_DATE"]).dt.date >= ds) & (pd.to_datetime(df["CLAIM_DATE"]).dt.date <= de)]
    if sel_fac: d = d[d["FACILITY_ID"].isin(sel_fac)]
    return d

def filter_sdoh(df):
    d = df[(pd.to_datetime(df["METRIC_MONTH"]).dt.date >= ds) & (pd.to_datetime(df["METRIC_MONTH"]).dt.date <= de)]
    return d

ehr    = filter_ehr(_ehr)
co     = filter_co(_co)
claims = filter_claims(_claims)
sdoh   = filter_sdoh(_sdoh)
train  = _train.copy()
if sel_dept: train = train[train["DEPARTMENT_ID"].isin(sel_dept)]
tickets = _tickets.copy()
if sel_dept: tickets = tickets[tickets["DEPARTMENT_ID"].isin(sel_dept)]


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
    readmit  = round(co["READMISSION_RATE"].mean() * 100, 1) if not co.empty else 0
    hcahps   = round(co["HCAHPS_SCORE"].mean(), 0) if not co.empty else 0
    hai      = round(co["HAI_RATE"].mean() * 10000, 2) if not co.empty else 0
    doc_comp = round(co["DOC_COMPLETION_RATE"].mean() * 100, 1) if not co.empty else 0
    cds_ovr  = round(co["CDS_OVERRIDE_RATE"].mean() * 100, 1) if not co.empty else 0
    pajama   = round(ehr["AFTER_HOURS_MINUTES"].mean(), 1) if not ehr.empty else 0
    dax_pct  = round(ehr["AI_ASSIST_USED"].mean() * 100, 1) if not ehr.empty else 0

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    with c1: kpi_card("30-Day Readmit", f"{readmit}%", "-0.9% vs prior yr", "inverse")
    with c2: kpi_card("HCAHPS Score", f"{int(hcahps)}/100", "+1.4 pts")
    with c3: kpi_card("HAI Rate /10K", f"{hai:.2f}", "-0.12", "inverse")
    with c4: kpi_card("Doc Completion", f"{doc_comp}%", "+2.1%")
    with c5: kpi_card("Pajama Time", f"{pajama:.1f} min", "-3.2 min", "inverse")
    with c6: kpi_card("DAX Adoption", f"{dax_pct}%", "+12.4%")

    section_header("📊", "Quality Performance Gauges")
    g1,g2,g3,g4 = st.columns(4)
    with g1: st.plotly_chart(gauge_chart(max(0, 100 - readmit * 5), "Readmit Score", 75, "#2563EB"), width="stretch")
    with g2: st.plotly_chart(gauge_chart(float(hcahps), "HCAHPS", 80, "#059669"), width="stretch")
    with g3: st.plotly_chart(gauge_chart(doc_comp, "Doc Completion", 90, "#7C3AED"), width="stretch")
    with g4: st.plotly_chart(gauge_chart(max(0, 100 - cds_ovr), "CDS Compliance", 60, "#D97706"), width="stretch")

    section_header("📈", "Monthly Trends")
    co1, co2 = st.columns(2)
    with co1:
        st.markdown("**30-Day Readmission Rate Trend**")
        trend = co.copy()
        trend["METRIC_MONTH"] = pd.to_datetime(trend["METRIC_MONTH"])
        trend = trend.groupby("METRIC_MONTH").agg(READMIT=("READMISSION_RATE", lambda x: round(x.mean()*100, 2))).reset_index()
        if not trend.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=trend["METRIC_MONTH"], y=trend["READMIT"], name="Readmission %",
                          fill="tozeroy", fillcolor="rgba(220,38,38,0.08)",
                          line=dict(color="#DC2626", width=2.5), mode="lines+markers", marker=dict(size=5)))
            fig.add_hline(y=15, line_dash="dot", line_color="#94A3B8", annotation_text="CMS Target: 15%",
                          annotation_font_color="#94A3B8")
            fig.add_shape(type="line", x0=AI_ROLLOUT_DATE, x1=AI_ROLLOUT_DATE, y0=0, y1=1, yref="paper",
                          line=dict(color="#059669", width=1.5, dash="dash"))
            fig.add_annotation(x=AI_ROLLOUT_DATE, y=0.95, yref="paper", text="DAX Rollout",
                               showarrow=False, font=dict(color="#059669", size=10))
            st.plotly_chart(chart_defaults(fig, 320), width="stretch")

    with co2:
        st.markdown("**Provider After-Hours (Pajama Time) Trend**")
        pt = ehr.copy()
        pt["USAGE_DATE"] = pd.to_datetime(pt["USAGE_DATE"])
        pt["MO"] = pt["USAGE_DATE"].dt.to_period("M").dt.to_timestamp()
        pt = pt.groupby("MO").agg(PAJAMA=("AFTER_HOURS_MINUTES", lambda x: round(x.mean(),1)),
                                    INBOX=("INBASKET_AFTER_HOURS_MIN", lambda x: round(x.mean(),1))).reset_index()
        if not pt.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=pt["MO"], y=pt["PAJAMA"], name="Total After-Hours",
                          fill="tozeroy", fillcolor="rgba(37,99,235,0.08)",
                          line=dict(color="#2563EB", width=2.5), mode="lines+markers", marker=dict(size=5)))
            fig.add_trace(go.Scatter(x=pt["MO"], y=pt["INBOX"], name="InBasket",
                          line=dict(color="#D97706", width=1.5, dash="dash")))
            fig.add_shape(type="line", x0=AI_ROLLOUT_DATE, x1=AI_ROLLOUT_DATE, y0=0, y1=1, yref="paper",
                          line=dict(color="#059669", width=1.5, dash="dash"))
            fig.add_annotation(x=AI_ROLLOUT_DATE, y=0.95, yref="paper", text="DAX Rollout",
                               showarrow=False, font=dict(color="#059669", size=10))
            fig = chart_defaults(fig, 320)
            fig.update_layout(yaxis_title="Minutes / Day")
            st.plotly_chart(fig, width="stretch")

    section_header("🏥", "Department Scorecard")
    corr = co.groupby("DEPARTMENT_NAME").agg(
        DOC_COMP=("DOC_COMPLETION_RATE", lambda x: round(x.mean()*100, 1)),
        READMIT=("READMISSION_RATE", lambda x: round(x.mean()*100, 1)),
        CDS_OVERRIDE=("CDS_OVERRIDE_RATE", lambda x: round(x.mean()*100, 1)),
        HCAHPS=("HCAHPS_SCORE", lambda x: round(x.mean(), 0)),
        ENCOUNTERS=("ENCOUNTER_COUNT", "sum"),
    ).reset_index()

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

    with st.expander(":material/code: View SQL — how this would look against live data"):
        st.code("""SELECT DEPARTMENT_NAME, AVG(DOC_COMPLETION_RATE)*100 AS doc_comp,
       AVG(READMISSION_RATE)*100 AS readmit, AVG(CDS_OVERRIDE_RATE)*100 AS cds_override
FROM CLINICAL_OUTCOMES WHERE METRIC_MONTH BETWEEN :start AND :end
GROUP BY DEPARTMENT_NAME;""", language="sql")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PAYER & CLAIMS INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    total_claims = len(claims)
    total_billed = claims["BILLED_AMOUNT"].sum()
    total_paid   = claims["PAID_AMOUNT"].sum()
    denied_amt   = claims[claims["CLAIM_STATUS"]=="Denied"]["BILLED_AMOUNT"].sum()
    denial_rate  = round(len(claims[claims["CLAIM_STATUS"]=="Denied"]) / max(total_claims,1) * 100, 1)
    appeal_sub   = claims["APPEAL_SUBMITTED"].sum()
    appeal_won   = claims["APPEAL_WON"].sum()
    appeal_win_rate = round(appeal_won / max(appeal_sub,1) * 100, 1)

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: kpi_card("Total Claims", f"{total_claims:,}")
    with c2: kpi_card("Revenue Collected", f"${total_paid:,.0f}", f"of ${total_billed:,.0f} billed")
    with c3: kpi_card("Denial Rate", f"{denial_rate}%", "Target < 8%", "inverse")
    with c4: kpi_card("Denied Revenue", f"${denied_amt:,.0f}", delta_color="off")
    with c5: kpi_card("Appeal Win Rate", f"{appeal_win_rate}%", "+5.2%")

    section_header("💰", "Revenue Waterfall")
    st.markdown("**Billed → Collected Revenue Flow**")
    contractual_adj = total_billed - total_paid - denied_amt
    fig = go.Figure(go.Waterfall(
        x=["Billed", "Contractual Adj.", "Denials", "Collected"],
        y=[total_billed, -contractual_adj, -denied_amt, 0],
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
        by_payer = claims.groupby(["PAYER_NAME","PAYER_TYPE"]).apply(
            lambda x: pd.Series({
                "CLAIMS": len(x),
                "DENIAL_RATE": round(len(x[x["CLAIM_STATUS"]=="Denied"]) / max(len(x),1) * 100, 1),
                "BILLED": round(x["BILLED_AMOUNT"].sum(), 0),
                "PAID": round(x["PAID_AMOUNT"].sum(), 0),
            })
        ).reset_index()
        by_payer = by_payer.sort_values("DENIAL_RATE", ascending=False)
        if not by_payer.empty:
            fig = px.bar(by_payer, x="PAYER_NAME", y="DENIAL_RATE", color="PAYER_TYPE",
                         color_discrete_map={"Government":"#2563EB","Commercial":"#7C3AED","Self-Pay":"#D97706"},
                         text="DENIAL_RATE", labels={"PAYER_NAME":"","DENIAL_RATE":"Denial Rate %"})
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig.add_hline(y=8, line_dash="dot", line_color="#DC2626", annotation_text="8% Target")
            st.plotly_chart(chart_defaults(fig, 340), width="stretch")

    with co2:
        st.markdown("**Top Denial Codes by Volume (Treemap)**")
        by_code = claims[claims["CLAIM_STATUS"]=="Denied"].groupby(["DENIAL_CODE","DENIAL_REASON"]).agg(
            CNT=("CLAIM_ID","count"),
            LOST_REVENUE=("BILLED_AMOUNT","sum")
        ).reset_index().sort_values("CNT", ascending=False).head(8)
        if not by_code.empty:
            fig = px.treemap(by_code, path=["DENIAL_CODE"], values="CNT", color="LOST_REVENUE",
                             color_continuous_scale=["#DBEAFE","#2563EB","#1E3A5F"],
                             hover_data=["DENIAL_REASON","LOST_REVENUE"],
                             labels={"CNT":"Claims","LOST_REVENUE":"Lost Revenue"})
            fig.update_layout(height=340, margin=dict(l=5,r=5,t=30,b=5))
            st.plotly_chart(fig, width="stretch")

    section_header("📅", "Monthly Claims Trend")
    st.markdown("**Revenue Collected vs Denial Rate — Monthly**")
    monthly = claims.copy()
    monthly["CLAIM_DATE"] = pd.to_datetime(monthly["CLAIM_DATE"])
    monthly["MO"] = monthly["CLAIM_DATE"].dt.to_period("M").dt.to_timestamp()
    monthly = monthly.groupby("MO").agg(
        CLAIMS=("CLAIM_ID","count"),
        DENIAL_RATE=("CLAIM_STATUS", lambda x: round((x=="Denied").mean()*100, 1)),
        REVENUE=("PAID_AMOUNT","sum")
    ).reset_index()
    if not monthly.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=monthly["MO"], y=monthly["REVENUE"], name="Revenue Collected",
                     marker_color="#2563EB", opacity=0.7, yaxis="y"))
        fig.add_trace(go.Scatter(x=monthly["MO"], y=monthly["DENIAL_RATE"], name="Denial Rate %",
                     line=dict(color="#DC2626", width=2.5), mode="lines+markers",
                     marker=dict(size=6), yaxis="y2"))
        fig = chart_defaults(fig, 320)
        fig.update_layout(yaxis=dict(title="Revenue ($)", side="left"),
                          yaxis2=dict(title="Denial Rate %", side="right", overlaying="y", range=[0,25]),
                          barmode="group")
        st.plotly_chart(fig, width="stretch")

    section_header("🔍", "Service Line Performance")
    by_sl = claims.groupby("SERVICE_LINE").agg(
        CLAIMS=("CLAIM_ID","count"),
        DENIAL_RATE=("CLAIM_STATUS", lambda x: round((x=="Denied").mean()*100, 1)),
        REVENUE=("PAID_AMOUNT", lambda x: round(x.sum(), 0)),
        AVG_DAYS=("DAYS_TO_PAYMENT", lambda x: round(x.mean(), 0)),
    ).reset_index().sort_values("REVENUE", ascending=False)
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
        st.code("""SELECT PAYER_NAME, COUNT(*) AS claims,
       SUM(CASE WHEN CLAIM_STATUS='Denied' THEN 1 ELSE 0 END)*100.0/COUNT(*) AS denial_rate,
       SUM(BILLED_AMOUNT) AS billed, SUM(PAID_AMOUNT) AS paid
FROM PAYER_CLAIMS GROUP BY PAYER_NAME ORDER BY denial_rate DESC;""", language="sql")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SDOH & POPULATION HEALTH
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    communities_n = sdoh["ZIP_CODE"].nunique() if not sdoh.empty else 0
    avg_sdoh = round(sdoh["COMPOSITE_SDOH_SCORE"].mean(), 0) if not sdoh.empty else 0
    avg_uninsured = round(sdoh["UNINSURED_PCT"].mean(), 1) if not sdoh.empty else 0
    avg_care_gap = round(sdoh["CARE_GAP_CLOSURE_PCT"].mean(), 1) if not sdoh.empty else 0
    avg_ed = round(sdoh["ED_VISIT_RATE_PER_1K"].mean(), 1) if not sdoh.empty else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: kpi_card("Communities Tracked", str(communities_n))
    with c2: kpi_card("Avg SDOH Risk Score", f"{int(avg_sdoh)}/100")
    with c3: kpi_card("Avg Uninsured", f"{avg_uninsured}%")
    with c4: kpi_card("Care Gap Closure", f"{avg_care_gap}%", "Target > 80%")
    with c5: kpi_card("Avg ED Rate /1K", f"{avg_ed}")

    section_header("🗺️", "Community Risk Map")
    community = sdoh.groupby(["COMMUNITY_NAME","ZIP_CODE","SDOH_RISK_TIER"]).agg(
        RISK_SCORE=("COMPOSITE_SDOH_SCORE","mean"),
        UNINSURED=("UNINSURED_PCT","mean"),
        INCOME=("MEDIAN_INCOME","mean"),
        ED_RATE=("ED_VISIT_RATE_PER_1K","mean"),
        CARE_GAP=("CARE_GAP_CLOSURE_PCT","mean"),
    ).reset_index()
    community["RISK_SCORE"] = community["RISK_SCORE"].round(0)
    community["INCOME"] = community["INCOME"].round(0)
    community["ED_RATE"] = community["ED_RATE"].round(1)

    co1, co2 = st.columns(2)
    with co1:
        st.markdown("**Income vs ED Utilization by Community**")
        if not community.empty:
            fig = px.scatter(community, x="INCOME", y="ED_RATE", size="RISK_SCORE",
                             color="SDOH_RISK_TIER", text="COMMUNITY_NAME",
                             color_discrete_map={"High":"#DC2626","Medium":"#D97706","Low":"#059669"},
                             labels={"INCOME":"Median Income ($)","ED_RATE":"ED Visits /1K"})
            fig.update_traces(textposition="top center", textfont_size=9)
            st.plotly_chart(chart_defaults(fig, 360), width="stretch")

    with co2:
        st.markdown("**SDOH Risk Distribution by Community**")
        if not community.empty:
            fig = px.sunburst(community, path=["SDOH_RISK_TIER","COMMUNITY_NAME"], values="RISK_SCORE",
                              color="RISK_SCORE", color_continuous_scale=["#DCFCE7","#FDE68A","#FCA5A5"],
                              labels={"RISK_SCORE":"SDOH Score"})
            fig.update_layout(height=360, margin=dict(l=5,r=5,t=30,b=5))
            st.plotly_chart(fig, width="stretch")

    section_header("📊", "Social Determinants Breakdown")
    co1, co2 = st.columns(2)
    with co1:
        st.markdown("**Barrier Prevalence by Community**")
        barriers = sdoh.groupby("COMMUNITY_NAME").agg(
            HOUSING=("HOUSING_INSTABILITY_PCT","mean"),
            TRANSPORT=("TRANSPORT_BARRIER_PCT","mean"),
            LANGUAGE=("LANGUAGE_BARRIER_PCT","mean"),
            UNINSURED=("UNINSURED_PCT","mean"),
        ).reset_index().sort_values("HOUSING", ascending=False)
        barriers = barriers.round(1)
        if not barriers.empty:
            fig = go.Figure()
            for col, color, name in [("HOUSING","#DC2626","Housing"),("TRANSPORT","#D97706","Transport"),
                                      ("LANGUAGE","#7C3AED","Language"),("UNINSURED","#2563EB","Uninsured")]:
                fig.add_trace(go.Bar(name=name, x=barriers["COMMUNITY_NAME"], y=barriers[col], marker_color=color))
            fig = chart_defaults(fig, 360)
            fig.update_layout(barmode="group", xaxis_tickangle=-35)
            st.plotly_chart(fig, width="stretch")

    with co2:
        st.markdown("**Chronic Condition Prevalence by SDOH Risk Tier**")
        conditions = sdoh.groupby(["CHRONIC_CONDITION","SDOH_RISK_TIER"]).agg(
            PREVALENCE=("PREVALENCE_PCT","mean"),
        ).reset_index().round(1)
        if not conditions.empty:
            fig = px.bar(conditions, x="CHRONIC_CONDITION", y="PREVALENCE", color="SDOH_RISK_TIER",
                         barmode="group",
                         color_discrete_map={"High":"#DC2626","Medium":"#D97706","Low":"#059669"},
                         labels={"CHRONIC_CONDITION":"","PREVALENCE":"Prevalence %"})
            st.plotly_chart(chart_defaults(fig, 360), width="stretch")

    section_header("📋", "Community Detail")
    detail = sdoh.groupby(["COMMUNITY_NAME","ZIP_CODE","SDOH_RISK_TIER"]).agg(
        SDOH_SCORE=("COMPOSITE_SDOH_SCORE","mean"),
        MEDIAN_INCOME=("MEDIAN_INCOME","mean"),
        UNINSURED_PCT=("UNINSURED_PCT","mean"),
        HEALTH_LITERACY=("HEALTH_LITERACY_SCORE","mean"),
        ED_RATE=("ED_VISIT_RATE_PER_1K","mean"),
        CARE_GAP_PCT=("CARE_GAP_CLOSURE_PCT","mean"),
        SCREENING_PCT=("PREVENTIVE_SCREENING_PCT","mean"),
    ).reset_index().round(1).sort_values("SDOH_SCORE", ascending=False)
    if not detail.empty:
        def hl_risk(row):
            t = row.get("SDOH_RISK_TIER","")
            if t == "High": return ["background-color:#FEE2E2"] * len(row)
            if t == "Medium": return ["background-color:#FEF9C3"] * len(row)
            return ["background-color:#DCFCE7"] * len(row)
        st.dataframe(detail.style.apply(hl_risk, axis=1), width="stretch", hide_index=True,
                     column_config={
                         "SDOH_SCORE": st.column_config.ProgressColumn("SDOH Score", min_value=0, max_value=100),
                         "CARE_GAP_PCT": st.column_config.ProgressColumn("Care Gap %", min_value=0, max_value=100),
                         "MEDIAN_INCOME": st.column_config.NumberColumn("Income", format="$%d"),
                         "HEALTH_LITERACY": st.column_config.ProgressColumn("Health Lit.", min_value=0, max_value=100),
                     })

    with st.expander(":material/code: View SQL"):
        st.code("""SELECT COMMUNITY_NAME, ZIP_CODE, SDOH_RISK_TIER,
       AVG(COMPOSITE_SDOH_SCORE) AS sdoh_score, AVG(MEDIAN_INCOME) AS income,
       AVG(ED_VISIT_RATE_PER_1K) AS ed_rate, AVG(CARE_GAP_CLOSURE_PCT) AS care_gap
FROM SDOH_POPULATION GROUP BY COMMUNITY_NAME, ZIP_CODE, SDOH_RISK_TIER
ORDER BY sdoh_score DESC;""", language="sql")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — AI & TECHNOLOGY ROI
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    ai_used = ehr[ehr["AI_ASSIST_USED"]]
    no_ai   = ehr[~ehr["AI_ASSIST_USED"]]
    ai_pct     = round(ehr["AI_ASSIST_USED"].mean() * 100, 1) if not ehr.empty else 0
    pajama_ai  = round(ai_used["AFTER_HOURS_MINUTES"].mean(), 1) if not ai_used.empty else 0
    pajama_no  = round(no_ai["AFTER_HOURS_MINUTES"].mean(), 1) if not no_ai.empty else 0
    delta_val  = round(pajama_no - pajama_ai, 1)
    note_delta = round(no_ai["NOTE_CLOSURE_AFTER_HOURS_MIN"].mean() - ai_used["NOTE_CLOSURE_AFTER_HOURS_MIN"].mean(), 1) if not ai_used.empty else 0

    ai_train_pct = round(
        train[train["COURSE_CATEGORY"].isin(["AI/ML","EHR Optimization"])]["STATUS"].eq("Completed").mean() * 100, 1
    ) if not train.empty else 0
    open_tickets = len(tickets[tickets["STATUS"].isin(["Open","In Progress"])])

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: kpi_card("DAX Adoption", f"{ai_pct}%", "+12.4%")
    with c2: kpi_card("Time Saved /Day", f"{delta_val:.1f} min", "per provider", "off")
    with c3: kpi_card("With AI", f"{pajama_ai:.1f} min", "after-hours", "off")
    with c4: kpi_card("AI Training Done", f"{ai_train_pct:.1f}%", "+8.2%")
    with c5: kpi_card("Open IT Tickets", str(open_tickets), delta_color="off")

    section_header("🤖", "AI Impact Analysis")
    co1, co2 = st.columns(2)
    with co1:
        st.markdown("**After-Hours Minutes: With vs Without DAX**")
        by_dept = ehr.groupby("DEPARTMENT_NAME").agg(
            WITH_AI=("AFTER_HOURS_MINUTES", lambda x: round(ehr.loc[x.index[ehr.loc[x.index,"AI_ASSIST_USED"]], "AFTER_HOURS_MINUTES"].mean(), 1)),
            WITHOUT_AI=("AFTER_HOURS_MINUTES", lambda x: round(ehr.loc[x.index[~ehr.loc[x.index,"AI_ASSIST_USED"]], "AFTER_HOURS_MINUTES"].mean(), 1)),
        ).reset_index().sort_values("WITHOUT_AI", ascending=False)
        if not by_dept.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Without AI", x=by_dept["DEPARTMENT_NAME"], y=by_dept["WITHOUT_AI"], marker_color="#94A3B8"))
            fig.add_trace(go.Bar(name="With AI (DAX)", x=by_dept["DEPARTMENT_NAME"], y=by_dept["WITH_AI"], marker_color="#2563EB"))
            fig = chart_defaults(fig, 360)
            fig.update_layout(barmode="group", xaxis_tickangle=-35, yaxis_title="After-Hours Min/Day")
            st.plotly_chart(fig, width="stretch")

    with co2:
        st.markdown("**DAX Adoption Rate Over Time**")
        at = ehr.copy()
        at["USAGE_DATE"] = pd.to_datetime(at["USAGE_DATE"])
        at["MO"] = at["USAGE_DATE"].dt.to_period("M").dt.to_timestamp()
        at = at.groupby("MO").agg(AI_PCT=("AI_ASSIST_USED", lambda x: round(x.mean()*100, 1))).reset_index()
        if not at.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=at["MO"], y=at["AI_PCT"], fill="tozeroy",
                          fillcolor="rgba(37,99,235,0.12)", line=dict(color="#2563EB", width=3),
                          mode="lines+markers", marker=dict(size=6)))
            fig.add_shape(type="line", x0=AI_ROLLOUT_DATE, x1=AI_ROLLOUT_DATE, y0=0, y1=1, yref="paper",
                          line=dict(color="#059669", width=2, dash="dash"))
            fig.add_annotation(x=AI_ROLLOUT_DATE, y=0.95, yref="paper", text="DAX Launch",
                               showarrow=False, font=dict(color="#059669", size=10))
            fig = chart_defaults(fig, 360)
            fig.update_layout(yaxis_title="DAX Adoption %")
            st.plotly_chart(fig, width="stretch")

    section_header("💡", "ROI Calculator")
    providers_using = int(HEALTH_SYSTEM["providers"] * ai_pct / 100)
    annual_hours_saved = providers_using * delta_val * 250 / 60
    physician_value = annual_hours_saved * 180

    rc1,rc2,rc3,rc4 = st.columns(4)
    with rc1: kpi_card("Providers Using DAX", str(providers_using))
    with rc2: kpi_card("Annual Hours Saved", f"{annual_hours_saved:,.0f} hrs")
    with rc3: kpi_card("Physician Time Value", f"${physician_value:,.0f}", "@ $180/hr", "off")
    with rc4: kpi_card("Investment ROI", f"{physician_value/2100000*100:.0f}%" if physician_value > 0 else "--", "on $2.1M investment")

    section_header("🧠", "AI Executive Briefing", "Pre-generated summary")
    with st.expander("📋 View Executive Summary", expanded=True):
        st.markdown(f"""
<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-left:4px solid #2563EB;
     padding:20px;border-radius:8px;line-height:1.8;font-size:13px;">

**1. System Performance Overview**<br>
MetroHealth Alliance is performing at or above benchmark on key quality metrics, with a 30-day readmission rate of {readmit}%
and an HCAHPS score of {int(hcahps)}/100. Documentation completion at {doc_comp}% reflects strong EHR adoption across most service lines.

**2. Areas of Concern**<br>
• CDS override rate of {cds_ovr}% — above the 50% safety threshold in Emergency Medicine and Hospitalist departments<br>
• Self-Pay denial rate of ~28% is 3.5× the 8% target, representing approximately $2.1M in recoverable revenue<br>
• Cedar Park and Industrial Corridor communities show SDOH composite scores above 75, driving above-average ED utilization<br>
• Average pajama time of {pajama:.1f} min/day remains above the 45-minute threshold in 6 of 15 departments

**3. Priority Actions for CMIO (Next 30 Days)**<br>
1. Accelerate DAX rollout in Cardiology and Hospitalist Medicine — highest after-hours burden, lowest AI adoption<br>
2. Launch targeted CDS alert review in Emergency Medicine — 64% override rate indicates alert fatigue<br>
3. Partner with Revenue Cycle to address CO-16 and CO-4 denial codes — represent 38% of total denied revenue<br>
4. Initiate SDOH care navigation program in Cedar Park (63107) and Industrial Corridor (63110)<br>
5. Review Self-Pay billing workflow — denial rate significantly exceeds commercial payer benchmarks

**4. Board Talking Points**<br>
• DAX AI investment is generating measurable ROI: {providers_using} providers saving {delta_val:.1f} min/day = ~${physician_value:,.0f} in annualized physician time value<br>
• HCAHPS trending up {'+1.4'} points — directly tied to improved documentation quality and reduced EHR burden<br>
• SDOH data now integrated into clinical workflow, enabling proactive outreach to high-risk communities

</div>
""", unsafe_allow_html=True)

    with st.expander(":material/code: View SQL"):
        st.code("""-- AI ROI: DAX vs non-DAX after-hours comparison
SELECT DEPARTMENT_NAME,
       AVG(CASE WHEN AI_ASSIST_USED THEN AFTER_HOURS_MINUTES END) AS with_ai,
       AVG(CASE WHEN NOT AI_ASSIST_USED THEN AFTER_HOURS_MINUTES END) AS without_ai
FROM EHR_DAILY_USAGE GROUP BY DEPARTMENT_NAME;""", language="sql")


# ── Footer ───────────────────────────────────────────────────────────────────
st.divider()
fc1,fc2,fc3 = st.columns(3)
with fc1:
    st.markdown("**Data Architecture**")
    st.caption("11 tables • 65K+ rows • Synthetic data • Zero compute cost")
with fc2:
    st.markdown("**Key CMIO Metrics**")
    st.caption("Quality • Claims • SDOH • AI ROI • Burnout")
with fc3:
    st.markdown(f"**{HEALTH_SYSTEM['name']}**")
    st.caption(f"{HEALTH_SYSTEM['hospitals']} Hospitals • {HEALTH_SYSTEM['providers']} Providers • {HEALTH_SYSTEM['revenue']}")
