import numpy as np
import pandas as pd
from datetime import date, timedelta

RNG = np.random.default_rng(42)

AI_ROLLOUT_DATE = "2025-10-01"
AI_ROLLOUT = pd.Timestamp("2025-10-01")

FACILITIES = [
    {"FACILITY_ID": f"FAC-{i:03d}", "FACILITY_NAME": name}
    for i, name in enumerate([
        "MetroHealth Main Campus", "North Regional Hospital", "South Medical Center",
        "East Community Hospital", "West Valley Hospital", "Lakeview Medical Center",
        "Riverside General", "Highland Health Center", "Oakwood Hospital",
        "Pineview Medical", "Cedar Ridge Hospital", "Summit Health Campus"
    ], 1)
]

DEPARTMENTS = [
    {"DEPARTMENT_ID": f"DEPT-{i:02d}", "DEPARTMENT_NAME": name, "SPECIALTY_GROUP": spec}
    for i, (name, spec) in enumerate([
        ("Cardiology", "Medicine"), ("Orthopedics", "Surgery"),
        ("Emergency Medicine", "Emergency"), ("Hospitalist Medicine", "Medicine"),
        ("Oncology", "Medicine"), ("Neurology", "Medicine"),
        ("General Surgery", "Surgery"), ("Obstetrics", "Surgery"),
        ("Pediatrics", "Medicine"), ("Pulmonology", "Medicine"),
        ("Radiology", "Diagnostic"), ("Gastroenterology", "Medicine"),
        ("Nephrology", "Medicine"), ("Urology", "Surgery"),
        ("Psychiatry", "Behavioral Health"),
    ], 1)
]

DEPT_NAMES = [d["DEPARTMENT_NAME"] for d in DEPARTMENTS]
DEPT_SPECS = {d["DEPARTMENT_NAME"]: d["SPECIALTY_GROUP"] for d in DEPARTMENTS}
DEPT_IDS = {d["DEPARTMENT_NAME"]: d["DEPARTMENT_ID"] for d in DEPARTMENTS}
FAC_IDS = [f["FACILITY_ID"] for f in FACILITIES]

START_DATE = pd.Timestamp("2025-03-01")
END_DATE = pd.Timestamp("2026-03-31")


import streamlit as st


@st.cache_data
def get_facilities_df():
    return pd.DataFrame(FACILITIES)


@st.cache_data
def get_departments_df():
    return pd.DataFrame(DEPARTMENTS)


@st.cache_data
def get_ehr_usage():
    rng = np.random.default_rng(42)
    rows = []
    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    for dept in DEPARTMENTS:
        base_pajama = rng.uniform(32, 68)
        base_adoption = rng.uniform(45, 88)
        for dt in dates:
            post_ai = dt >= AI_ROLLOUT
            ai_boost = rng.uniform(0.70, 0.85) if post_ai else 1.0
            ai_used = post_ai and (rng.random() < rng.uniform(0.15, 0.60))
            pajama = max(5, base_pajama * (0.75 if ai_used else 1.0) * ai_boost * rng.uniform(0.85, 1.15))
            rows.append({
                "USAGE_DATE": dt.date(),
                "DEPARTMENT_NAME": dept["DEPARTMENT_NAME"],
                "DEPARTMENT_ID": dept["DEPARTMENT_ID"],
                "FACILITY_ID": FAC_IDS[rng.integers(0, 12)],
                "PROVIDER_ID": f"PROV-{rng.integers(1, 221):03d}",
                "SPECIALTY_GROUP": dept["SPECIALTY_GROUP"],
                "AFTER_HOURS_MINUTES": round(pajama, 1),
                "INBASKET_AFTER_HOURS_MIN": round(pajama * rng.uniform(0.35, 0.50), 1),
                "NOTE_CLOSURE_AFTER_HOURS_MIN": round(pajama * rng.uniform(0.25, 0.40), 1),
                "CHART_REVIEW_AFTER_HOURS_MIN": round(pajama * rng.uniform(0.10, 0.20), 1),
                "INBASKET_MESSAGES_RECEIVED": int(rng.integers(8, 32)),
                "MYCHART_MESSAGES": int(rng.integers(2, 15)),
                "FEATURE_ADOPTION_SCORE": min(100, round(base_adoption * (1.12 if post_ai else 1.0) * rng.uniform(0.92, 1.08), 1)),
                "CDS_ALERTS_FIRED": int(rng.integers(3, 18)),
                "CDS_ALERTS_OVERRIDDEN": int(rng.integers(1, 10)),
                "ORDER_SETS_USED": int(rng.integers(2, 12)),
                "ORDERS_PLACED": int(rng.integers(8, 22)),
                "AVG_NOTE_COMPLETION_MIN": round(rng.uniform(6, 22), 1),
                "AI_ASSIST_USED": ai_used,
            })
    return pd.DataFrame(rows)


@st.cache_data
def get_clinical_outcomes():
    rng = np.random.default_rng(42)
    rows = []
    months = pd.date_range(START_DATE, END_DATE, freq="MS")
    fac_ids = FAC_IDS
    for dept in DEPARTMENTS:
        base_readmit = rng.uniform(0.08, 0.22)
        base_hcahps = rng.uniform(72, 94)
        for mo in months:
            for fac_id in fac_ids[:6]:
                rows.append({
                    "METRIC_MONTH": mo.date(),
                    "DEPARTMENT_NAME": dept["DEPARTMENT_NAME"],
                    "DEPARTMENT_ID": dept["DEPARTMENT_ID"],
                    "FACILITY_ID": fac_id,
                    "READMISSION_RATE": round(max(0.04, base_readmit * rng.uniform(0.88, 1.12)), 4),
                    "HAI_RATE": round(rng.uniform(0.0002, 0.0018), 5),
                    "HCAHPS_SCORE": round(min(100, base_hcahps * rng.uniform(0.96, 1.04)), 1),
                    "DOC_COMPLETION_RATE": round(rng.uniform(0.72, 0.97), 4),
                    "CDS_OVERRIDE_RATE": round(rng.uniform(0.28, 0.72), 4),
                    "ORDER_SET_COMPLIANCE": round(rng.uniform(0.45, 0.88), 4),
                    "ENCOUNTER_COUNT": int(rng.integers(120, 480)),
                })
    return pd.DataFrame(rows)


@st.cache_data
def get_payer_claims():
    rng = np.random.default_rng(42)
    payers = [
        ("Medicare", "Government"), ("Medicaid", "Government"),
        ("Blue Cross Blue Shield", "Commercial"), ("UnitedHealthcare", "Commercial"),
        ("Aetna", "Commercial"), ("Cigna", "Commercial"), ("Self-Pay", "Self-Pay"),
    ]
    payer_weights = [0.38, 0.22, 0.18, 0.12, 0.05, 0.03, 0.02]
    service_lines = ["Cardiology", "Orthopedics", "Oncology", "Primary Care",
                     "Neurology", "Pulmonology", "General Surgery", "Emergency Medicine"]
    denial_codes = [
        ("CO-4", "Procedure code inconsistent with modifier"),
        ("CO-16", "Claim lacks information needed for adjudication"),
        ("CO-18", "Duplicate claim/service"),
        ("CO-45", "Charges exceed fee schedule"),
        ("CO-97", "Payment adjusted: already adjudicated"),
        ("CO-29", "Time limit for filing has expired"),
        ("CO-50", "Non-covered services"),
        ("CO-167", "Diagnosis not covered"),
        ("PR-1", "Deductible amount"),
        ("PR-2", "Coinsurance amount"),
    ]
    rows = []
    n = 8500
    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    claim_dates = rng.choice(dates, size=n)
    payer_idx = rng.choice(len(payers), size=n, p=payer_weights)
    sl_idx = rng.integers(0, len(service_lines), size=n)
    dc_idx = rng.integers(0, len(denial_codes), size=n)
    fac_idx = rng.integers(0, 12, size=n)
    billed = rng.uniform(800, 45000, size=n)
    denial_roll = rng.integers(1, 101, size=n)
    appeal_roll = rng.integers(1, 101, size=n)
    for i in range(n):
        status = "Denied" if denial_roll[i] <= 12 else ("Pending" if denial_roll[i] <= 18 else "Paid")
        denied = status == "Denied"
        paid_amt = round(billed[i] * rng.uniform(0.65, 0.95), 2) if status == "Paid" else 0
        appeal_sub = denied and appeal_roll[i] <= 45
        appeal_won = appeal_sub and appeal_roll[i] <= 25
        rows.append({
            "CLAIM_ID": f"CLM-{i+1:06d}",
            "CLAIM_DATE": pd.Timestamp(claim_dates[i]).date(),
            "PAYER_NAME": payers[payer_idx[i]][0],
            "PAYER_TYPE": payers[payer_idx[i]][1],
            "SERVICE_LINE": service_lines[sl_idx[i]],
            "FACILITY_ID": FAC_IDS[fac_idx[i]],
            "BILLED_AMOUNT": round(billed[i], 2),
            "CLAIM_STATUS": status,
            "DENIAL_CODE": denial_codes[dc_idx[i]][0] if denied else None,
            "DENIAL_REASON": denial_codes[dc_idx[i]][1] if denied else None,
            "PAID_AMOUNT": paid_amt,
            "APPEAL_SUBMITTED": appeal_sub,
            "APPEAL_WON": appeal_won,
            "DAYS_TO_PAYMENT": int(rng.integers(3, 91)),
        })
    return pd.DataFrame(rows)


@st.cache_data
def get_sdoh_population():
    rng = np.random.default_rng(42)
    zips = [
        ("63101", "Downtown Metro",      28500, 42000, 14, True,  22, 58, 18, 12),
        ("63102", "North Heights",        35200, 38500, 18, True,  28, 45, 25, 19),
        ("63103", "Westside Commons",     41000, 55000,  8, False, 12, 72,  9,  6),
        ("63104", "East River District",  22800, 32000, 22, True,  35, 38, 31, 24),
        ("63105", "South Lake",           48000, 72000,  4, False,  6, 85,  4,  3),
        ("63106", "Midtown",              31500, 48000, 11, False, 15, 65, 13,  8),
        ("63107", "Cedar Park",           19200, 29000, 25, True,  38, 35, 34, 28),
        ("63108", "Riverside",            26700, 44000, 12, False, 18, 62, 15, 10),
        ("63109", "Harbor View",          37800, 61000,  6, False,  9, 78,  7,  5),
        ("63110", "Industrial Corridor",  15400, 27500, 28, True,  42, 32, 38, 31),
    ]
    conditions = [
        ("Diabetes", 0.12), ("Hypertension", 0.28), ("COPD", 0.08),
        ("Heart Failure", 0.06), ("Depression", 0.15), ("Asthma", 0.09),
    ]
    months = pd.date_range(START_DATE, END_DATE, freq="MS")
    rows = []
    for (zip_code, community, pop, income, uninsured, food_desert,
         housing, literacy, transport, language) in zips:
        risk_tier = "High" if income < 35000 and uninsured > 18 else ("Medium" if income < 50000 or uninsured > 10 else "Low")
        sdoh_score = int((uninsured/100 * 25) + (housing/100 * 20) + (transport/100 * 20) + (language/100 * 15) + ((100 - literacy)/100 * 20)) * 100 // 100
        sdoh_score = min(100, max(0, sdoh_score))
        for mo in months:
            for cond_name, base_prev in conditions:
                prevalence = round(max(0, base_prev + (1.0 - income / 80000) * 0.08 + rng.uniform(-0.02, 0.02)) * 100, 1)
                rows.append({
                    "ZIP_CODE": zip_code,
                    "COMMUNITY_NAME": community,
                    "METRIC_MONTH": mo.date(),
                    "POPULATION": pop,
                    "MEDIAN_INCOME": income,
                    "UNINSURED_PCT": float(uninsured),
                    "FOOD_DESERT": food_desert,
                    "HOUSING_INSTABILITY_PCT": float(housing),
                    "HEALTH_LITERACY_SCORE": float(literacy),
                    "TRANSPORT_BARRIER_PCT": float(transport),
                    "LANGUAGE_BARRIER_PCT": float(language),
                    "CHRONIC_CONDITION": cond_name,
                    "PREVALENCE_PCT": prevalence,
                    "CARE_GAP_CLOSURE_PCT": round(rng.uniform(55, 92), 1),
                    "ED_VISIT_RATE_PER_1K": round(rng.uniform(8, 35), 1),
                    "READMISSION_RATE_PCT": round(rng.uniform(3, 18), 1),
                    "PREVENTIVE_SCREENING_PCT": round(rng.uniform(40, 85), 1),
                    "SDOH_RISK_TIER": risk_tier,
                    "COMPOSITE_SDOH_SCORE": sdoh_score,
                })
    return pd.DataFrame(rows)


@st.cache_data
def get_training_lms():
    rng = np.random.default_rng(42)
    categories = ["EHR Basics", "Clinical Documentation", "AI/ML", "EHR Optimization",
                  "Compliance", "Patient Safety", "Order Sets", "CDS Training"]
    rows = []
    for dept in DEPARTMENTS:
        for cat in categories:
            n_providers = rng.integers(8, 25)
            for _ in range(n_providers):
                roll = rng.random()
                status = "Completed" if roll > 0.28 else ("In Progress" if roll > 0.12 else "Not Started")
                rows.append({
                    "DEPARTMENT_ID": dept["DEPARTMENT_ID"],
                    "DEPARTMENT_NAME": dept["DEPARTMENT_NAME"],
                    "FACILITY_ID": FAC_IDS[rng.integers(0, 12)],
                    "COURSE_CATEGORY": cat,
                    "STATUS": status,
                })
    return pd.DataFrame(rows)


@st.cache_data
def get_support_tickets():
    rng = np.random.default_rng(42)
    rows = []
    for i in range(2475):
        status = rng.choice(["Open", "In Progress", "Resolved", "Closed"],
                             p=[0.12, 0.10, 0.45, 0.33])
        rows.append({
            "TICKET_ID": f"TKT-{i+1:05d}",
            "DEPARTMENT_ID": DEPARTMENTS[rng.integers(0, 15)]["DEPARTMENT_ID"],
            "FACILITY_ID": FAC_IDS[rng.integers(0, 12)],
            "STATUS": status,
            "PRIORITY": rng.choice(["Critical", "High", "Medium", "Low"], p=[0.05, 0.20, 0.45, 0.30]),
        })
    return pd.DataFrame(rows)
