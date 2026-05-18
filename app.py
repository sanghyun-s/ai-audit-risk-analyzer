"""
app.py — Streamlit UI for the AI Audit Risk Analyzer (Phase 1 MVP).

Flow:
  1. Client onboarding form (entity type, benchmark, detection sensitivity)
  2. Auto-compute materiality thresholds and display banner
  3. CSV upload → column validation → feature engineering → ML scoring
  4. Display flagged transaction table + two Plotly charts

No GPT yet — that's Phase 4. The goal of Phase 1 is the audit-analytics
spine: upload CSV → see PCAOB-labeled risk table.

Run locally:  streamlit run app.py
"""
from __future__ import annotations

import io

import pandas as pd
import plotly.express as px
import streamlit as st

from features import (
    REQUIRED_COLUMNS,
    clean_gl_data,
    engineer_features,
    get_feature_columns,
    validate_required_columns,
)
from model import SENSITIVITY_MAP, run_isolation_forest
from scoring import apply_scoring


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI Audit Risk Analyzer",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 AI Audit Risk Analyzer")
st.caption(
    "ML anomaly detection + materiality-calibrated risk scoring + PCAOB-aligned "
    "labels for QuickBooks GL exports."
)


# ---------------------------------------------------------------------------
# Entity benchmark labels — change with entity_type selection
# ---------------------------------------------------------------------------

BENCHMARK_LABELS: dict[str, str] = {
    "Private for-profit": "EBT (Earnings Before Tax)",
    "Public company":     "Net Income",
    "Non-profit":         "Total Expenses",
    "Fund":               "Net Asset Value (NAV)",
}

# Public companies use 5% of benchmark for FS materiality; private 4%.
def fs_pct_for_entity(entity_type: str) -> float:
    return 0.05 if entity_type == "Public company" else 0.04


# ---------------------------------------------------------------------------
# Sidebar — client onboarding form
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Client Profile")
    st.caption("These inputs configure materiality and detection risk for the entire analysis.")

    entity_type = st.selectbox(
        "Entity type",
        options=list(BENCHMARK_LABELS.keys()),
        index=0,
    )

    benchmark_label = BENCHMARK_LABELS[entity_type]
    benchmark_figure = st.number_input(
        f"Benchmark figure — {benchmark_label}",
        min_value=0.0,
        value=150_000.0,
        step=1_000.0,
        format="%.2f",
        help="The income/expense/NAV figure used as the materiality base.",
    )

    detection_sensitivity = st.selectbox(
        "Detection sensitivity",
        options=list(SENSITIVITY_MAP.keys()),
        index=1,  # Balanced (0.05) default
        help="Maps to Isolation Forest contamination. Lower = stricter, fewer "
             "transactions flagged. Higher = looser, more flagged.",
    )

    st.markdown("---")
    st.markdown(
        "**Tier 1 MVP** — Phase 1 of 5.  \n"
        "GPT narrative layer is Phase 4."
    )


# ---------------------------------------------------------------------------
# Compute materiality thresholds — visible at all times
# ---------------------------------------------------------------------------

fs_pct = fs_pct_for_entity(entity_type)
fs_materiality = benchmark_figure * fs_pct
performance_materiality = fs_materiality * 0.50
transaction_materiality = fs_materiality * 0.80

# Persist for downstream tabs / future phases
st.session_state["fs_materiality"] = fs_materiality
st.session_state["performance_materiality"] = performance_materiality
st.session_state["transaction_materiality"] = transaction_materiality

st.subheader("Materiality Thresholds")
mcol1, mcol2, mcol3 = st.columns(3)
mcol1.metric(
    f"FS Materiality ({fs_pct:.0%} of benchmark)",
    f"${fs_materiality:,.0f}",
)
mcol2.metric(
    "Performance Materiality (50% of FS)",
    f"${performance_materiality:,.0f}",
)
mcol3.metric(
    "Transaction Materiality (80% of FS)",
    f"${transaction_materiality:,.0f}",
)
st.caption(
    "Methodology: FS materiality is derived from the entity benchmark. Performance "
    "and transaction materiality are auditor-judgment haircuts used to set scoping "
    "and individual-item thresholds."
)

st.markdown("---")


# ---------------------------------------------------------------------------
# CSV upload
# ---------------------------------------------------------------------------

st.subheader("1. Upload General Ledger CSV")
st.caption(
    f"Required columns: `{'`, `'.join(REQUIRED_COLUMNS)}`. "
    "A sample QuickBooks-style GL is included in the repository at "
    "`sample_data/sample_gl.csv`."
)

uploaded = st.file_uploader("Upload your GL export (.csv)", type=["csv"])

if uploaded is None:
    st.info("Awaiting CSV upload. Use the sample_gl.csv in sample_data/ if you "
            "just want to try the demo.")
    st.stop()

# Read CSV
try:
    raw_df = pd.read_csv(uploaded)
except Exception as e:  # pragma: no cover — Streamlit surfaces this
    st.error(f"Could not read CSV: {e}")
    st.stop()

ok, missing = validate_required_columns(raw_df)
if not ok:
    st.error(f"Uploaded CSV is missing required columns: {missing}")
    st.stop()

st.success(f"Loaded {len(raw_df):,} rows × {raw_df.shape[1]} columns.")
with st.expander("Preview raw GL (first 10 rows)", expanded=False):
    st.dataframe(raw_df.head(10), use_container_width=True)


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

st.subheader("2. Feature Engineering")

with st.spinner("Cleaning data and engineering 6 audit-risk features..."):
    cleaned_df = clean_gl_data(raw_df)
    feat_df = engineer_features(cleaned_df)
    feature_cols = get_feature_columns()

# Feature summary metrics — show "how the app reads your GL" before ML runs.
fcol1, fcol2, fcol3, fcol4, fcol5 = st.columns(5)
fcol1.metric("Round-number transactions", int(feat_df["is_round_number"].sum()))
fcol2.metric("Weekend postings",          int(feat_df["is_weekend_posting"].sum()))
fcol3.metric("Missing descriptions",      int(feat_df["missing_description"].sum()))
fcol4.metric("New-vendor transactions",   int(feat_df["is_new_vendor"].sum()))
fcol5.metric("Near approval threshold",   int(feat_df["is_near_approval_threshold"].sum()))

with st.expander("Preview engineered features (first 10 rows)", expanded=False):
    preview_cols = (
        ["date", "account_name", "vendor", "amount"] + feature_cols
    )
    st.dataframe(feat_df[preview_cols].head(10), use_container_width=True)


# ---------------------------------------------------------------------------
# ML scoring + audit-logic scoring
# ---------------------------------------------------------------------------

st.subheader("3. Isolation Forest + Materiality Filter")

with st.spinner("Running Isolation Forest..."):
    scored_df = run_isolation_forest(
        feat_df,
        feature_cols=feature_cols,
        detection_sensitivity=detection_sensitivity,
    )

with st.spinner("Applying materiality filter and PCAOB labeling..."):
    scored_df = apply_scoring(
        scored_df,
        fs_materiality=fs_materiality,
        performance_materiality=performance_materiality,
        transaction_materiality=transaction_materiality,
    )

# ---- Headline summary ----
total = len(scored_df)
flagged_df = scored_df[scored_df["flagged_status"] == "Flagged"].copy()
n_flagged = len(flagged_df)
pct_flagged = (n_flagged / total * 100) if total else 0.0

scol1, scol2, scol3, scol4 = st.columns(4)
scol1.metric("Total transactions analyzed", f"{total:,}")
scol2.metric("Flagged (High + Medium)", f"{n_flagged:,}")
scol3.metric("Flagged %", f"{pct_flagged:.1f}%")
scol4.metric(
    "Overall risk rating",
    "Elevated" if pct_flagged > 5 else "Moderate" if pct_flagged > 2 else "Low",
)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

st.subheader("4. Risk Distribution")

ccol1, ccol2 = st.columns(2)

# Chart 1: count of flagged transactions by PCAOB tier
with ccol1:
    tier_counts = (
        scored_df["pcaob_label"]
        .value_counts()
        .reindex([
            "Potential Material Weakness Indicator",
            "Potential Significant Deficiency",
            "Monitor — Below Escalation Threshold",
        ], fill_value=0)
        .reset_index()
    )
    tier_counts.columns = ["pcaob_label", "count"]
    fig1 = px.bar(
        tier_counts,
        x="pcaob_label",
        y="count",
        title="Transactions by PCAOB Risk Tier",
        labels={"pcaob_label": "PCAOB tier", "count": "Transaction count"},
        color="pcaob_label",
        color_discrete_map={
            "Potential Material Weakness Indicator": "#c0392b",
            "Potential Significant Deficiency":      "#e67e22",
            "Monitor — Below Escalation Threshold":  "#7f8c8d",
        },
    )
    fig1.update_layout(showlegend=False, xaxis_tickangle=-15)
    st.plotly_chart(fig1, use_container_width=True)

# Chart 2: top accounts by flagged amount
with ccol2:
    if n_flagged > 0:
        top_accounts = (
            flagged_df.groupby("account_name")["abs_amount"]
            .sum()
            .sort_values(ascending=True)
            .tail(10)
            .reset_index()
        )
        fig2 = px.bar(
            top_accounts,
            x="abs_amount",
            y="account_name",
            orientation="h",
            title="Top Accounts by Flagged Amount",
            labels={"abs_amount": "Total flagged amount ($)", "account_name": ""},
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No flagged transactions — nothing to rank.")


# ---------------------------------------------------------------------------
# Flagged transaction table
# ---------------------------------------------------------------------------

st.subheader("5. Flagged Transactions")

show_monitor = st.checkbox(
    "Also show Monitor rows (full output, not just flagged)", value=False
)
display_df = scored_df if show_monitor else flagged_df

display_cols = [
    "date", "account_name", "vendor", "amount",
    "anomaly_score", "raw_tier", "final_tier", "pcaob_label",
    "materiality_annotation", "active_flags",
]
# Some columns may be missing if df is empty — guard against KeyError
display_cols = [c for c in display_cols if c in display_df.columns]

st.dataframe(
    display_df[display_cols].reset_index(drop=True),
    use_container_width=True,
    height=420,
)

# CSV download
csv_buffer = io.StringIO()
display_df[display_cols].to_csv(csv_buffer, index=False)
st.download_button(
    "Download flagged transactions (CSV)",
    data=csv_buffer.getvalue(),
    file_name="flagged_transactions.csv",
    mime="text/csv",
)


# ---------------------------------------------------------------------------
# Footer / methodology
# ---------------------------------------------------------------------------

with st.expander("Methodology and limitations", expanded=False):
    st.markdown(
        """
**Pipeline.** GL CSV → 6 engineered features → StandardScaler → IsolationForest
(`n_estimators=200`, contamination set by detection sensitivity) → raw_tier from
fixed score bins → materiality filter → final_tier → PCAOB-style label.

**Tier 1 features.**
`amount_zscore_by_account` (ARP — account-level magnitude),
`is_round_number` (PCAOB AS 2401 fraud indicator),
`is_weekend_posting` (unusual posting timing),
`missing_description` (documentation control gap),
`is_new_vendor` (misappropriation opportunity),
`is_near_approval_threshold` (limit-test / invoice splitting).

**Limitations.** This is a Phase 1 MVP. It identifies *risk indicators* using
statistical anomaly detection and materiality thresholds. It does not determine
intent, conclude fraud, or issue audit opinions. Findings should be corroborated
with documentary evidence and discussions with management per AU-C 315 and
PCAOB AS 2401.
        """
    )
