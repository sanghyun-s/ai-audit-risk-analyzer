"""
features.py — raw GL CSV → cleaned dataframe + 12 engineered feature columns.

Phase 2: T1 features (6) unchanged from Phase 1, plus 6 new T2 features.

Tier 1 (MVP, used for the ML matrix):
  * amount_zscore_by_account
  * is_round_number
  * is_weekend_posting
  * missing_description
  * is_new_vendor
  * is_near_approval_threshold

Tier 2 (added for display + Phase 3 qualitative override):
  * control_gap_score          — composite (missing_desc + weekend)
  * fraud_flag_count           — count of fraud-indicator flags
  * fraud_risk_flag            — fraud_flag_count >= 2  → triggers override
  * period_over_period_pct     — account % change vs prior month
  * vendor_concentration_pct   — vendor share of total disbursements
  * is_year_end_concentration  — posted in last 10 days of audit period
  * is_non_standard_pattern    — debit/credit pairing outside the 6 standards

T2 features are computed alongside T1 but are NOT added to the ML feature
matrix by default — that would re-double-count signals the IF already sees.
T2 columns are display + override-rule fuel for Phase 3.
"""
from __future__ import annotations

from datetime import date

import pandas as pd


# ---- Required GL columns ----
REQUIRED_COLUMNS: list[str] = [
    "date",
    "amount",
    "account_code",
    "account_name",
    "vendor",
    "description",
    "journal_ref",
]

# Optional columns added in Phase 2 schema. If absent, the dependent T2 features
# fall back to safe defaults so the pipeline still runs.
OPTIONAL_COLUMNS: list[str] = ["debit_amount", "credit_amount", "dr_cr_pattern"]

APPROVAL_THRESHOLDS: list[int] = [5000, 10000, 25000]

# Tier 1 feature columns — these go into the ML feature matrix
FEATURE_COLS: list[str] = [
    "amount_zscore_by_account",
    "is_round_number",
    "is_weekend_posting",
    "missing_description",
    "is_new_vendor",
    "is_near_approval_threshold",
]

# Tier 2 feature columns — displayed and used by Phase 3 override rules
T2_FEATURE_COLS: list[str] = [
    "control_gap_score",
    "fraud_flag_count",
    "fraud_risk_flag",
    "period_over_period_pct",
    "vendor_concentration_pct",
    "is_year_end_concentration",
    "is_non_standard_pattern",
]

# Subset of T1 features that count as "fraud indicators" for fraud_flag_count.
# Used to compute the qualitative-override trigger.
FRAUD_FLAG_COLS: list[str] = [
    "is_round_number",
    "is_weekend_posting",
    "missing_description",
    "is_new_vendor",
    "is_near_approval_threshold",
]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_required_columns(df: pd.DataFrame) -> tuple[bool, list[str]]:
    """Return (ok, missing_columns). Optional columns not checked here."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    return (len(missing) == 0, missing)


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------

def clean_gl_data(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce dtypes and add abs_amount. Does not mutate input."""
    df = df.copy()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["abs_amount"] = df["amount"].abs()

    # Optional numeric coercion
    for col in ("debit_amount", "credit_amount"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    for col in ("vendor", "description", "account_name", "account_code"):
        if col in df.columns:
            df[col] = df[col].astype("string")

    return df


# ---------------------------------------------------------------------------
# Tier 1 features
# ---------------------------------------------------------------------------

def _is_round_number(amount: float) -> int:
    if pd.isna(amount):
        return 0
    return int(abs(amount) % 100 == 0)


def _near_approval_threshold(amount: float) -> int:
    if pd.isna(amount):
        return 0
    amount = abs(amount)
    for threshold in APPROVAL_THRESHOLDS:
        if threshold * 0.95 <= amount < threshold:
            return 1
    return 0


def _amount_zscore_by_account(df: pd.DataFrame) -> pd.Series:
    def _z(group: pd.Series) -> pd.Series:
        std = group.std(ddof=0)
        if std == 0 or pd.isna(std):
            return pd.Series(0.0, index=group.index)
        return (group - group.mean()) / std

    return (
        df.groupby("account_name", group_keys=False)["abs_amount"].apply(_z)
    )


def _add_tier1_features(df: pd.DataFrame) -> pd.DataFrame:
    df["amount_zscore_by_account"] = _amount_zscore_by_account(df)
    df["is_round_number"] = df["abs_amount"].apply(_is_round_number).astype(int)
    df["is_weekend_posting"] = df["date"].dt.weekday.isin([5, 6]).astype(int)
    df["missing_description"] = (
        df["description"].isna()
        | (df["description"].astype(str).str.strip() == "")
        | (df["description"].astype(str).str.strip().str.lower() == "nan")
    ).astype(int)

    vendor_counts = df["vendor"].fillna("UNKNOWN").value_counts()
    df["vendor_txn_count"] = df["vendor"].fillna("UNKNOWN").map(vendor_counts)
    df["is_new_vendor"] = (df["vendor_txn_count"] < 3).astype(int)

    df["is_near_approval_threshold"] = (
        df["abs_amount"].apply(_near_approval_threshold).astype(int)
    )
    return df


# ---------------------------------------------------------------------------
# Tier 2 features
# ---------------------------------------------------------------------------

def add_control_gap_score(df: pd.DataFrame) -> pd.DataFrame:
    """Composite control-gap proxy: missing_description + is_weekend_posting.
    Range 0–2. Higher = more documentation / authorization control gaps."""
    df["control_gap_score"] = (
        df["missing_description"].astype(int) + df["is_weekend_posting"].astype(int)
    )
    return df


def add_fraud_flag_count(df: pd.DataFrame) -> pd.DataFrame:
    """Sum of the 5 fraud-indicator binary flags. fraud_risk_flag fires when
    2 or more are active simultaneously — this is the qualitative override
    trigger in Phase 3."""
    df["fraud_flag_count"] = df[FRAUD_FLAG_COLS].sum(axis=1).astype(int)
    df["fraud_risk_flag"] = (df["fraud_flag_count"] >= 2).astype(int)
    return df


def add_period_over_period_pct(df: pd.DataFrame) -> pd.DataFrame:
    """Account-level month-over-month % change in total amount.

    The same value is broadcast to every row of that (account, month) — so the
    user can see, on a flagged row, the month's swing for that account.
    Months with no prior data get 0.
    """
    df["_month"] = df["date"].dt.to_period("M")
    monthly = (
        df.groupby(["account_name", "_month"])["abs_amount"].sum()
          .groupby(level=0).pct_change()
          .reset_index()
          .rename(columns={"abs_amount": "period_over_period_pct"})
    )
    monthly["period_over_period_pct"] = (
        monthly["period_over_period_pct"].fillna(0) * 100
    )
    df = df.merge(monthly, on=["account_name", "_month"], how="left")
    df = df.drop(columns=["_month"])
    return df


def add_vendor_concentration_pct(df: pd.DataFrame) -> pd.DataFrame:
    """Vendor's share of total disbursements (debit-natural rows only).

    For rows where debit_amount is available, use that. Otherwise approximate
    as the row's abs_amount when the account is expense-like (codes 5xxx-7xxx).
    Same value broadcast to every row of that vendor.
    """
    if "debit_amount" in df.columns:
        disbursement_basis = df["debit_amount"]
    else:
        # Approximate: rows on expense-like accounts count as disbursements
        is_disb = df["account_code"].astype(str).str.match(r"^[567]\d{3}$")
        disbursement_basis = df["abs_amount"].where(is_disb, 0)

    total = disbursement_basis.sum()
    if total <= 0:
        df["vendor_concentration_pct"] = 0.0
        return df

    by_vendor = (
        pd.DataFrame({"vendor": df["vendor"], "disb": disbursement_basis})
        .groupby("vendor")["disb"].sum()
    )
    pct = (by_vendor / total * 100).rename("vendor_concentration_pct")
    df = df.merge(pct.reset_index(), on="vendor", how="left")
    df["vendor_concentration_pct"] = df["vendor_concentration_pct"].fillna(0)
    return df


def add_year_end_concentration(
    df: pd.DataFrame,
    period_end: date | None = None,
    window_days: int = 10,
) -> pd.DataFrame:
    """1 if the transaction was posted in the last `window_days` of the period.
    Defaults to max(date) in the dataset if period_end isn't provided."""
    if period_end is None:
        period_end_ts = df["date"].max()
    else:
        period_end_ts = pd.Timestamp(period_end)
    cutoff = period_end_ts - pd.Timedelta(days=window_days - 1)
    df["is_year_end_concentration"] = (
        (df["date"] >= cutoff) & (df["date"] <= period_end_ts)
    ).astype(int)
    return df


def add_non_standard_pattern(df: pd.DataFrame) -> pd.DataFrame:
    """1 if the row's dr_cr_pattern is 'non_standard'. Requires the optional
    dr_cr_pattern column from the Phase 2 schema; falls back to 0 otherwise."""
    if "dr_cr_pattern" in df.columns:
        df["is_non_standard_pattern"] = (
            df["dr_cr_pattern"].astype(str).str.lower().eq("non_standard")
            .astype(int)
        )
    else:
        df["is_non_standard_pattern"] = 0
    return df


def _add_tier2_features(
    df: pd.DataFrame,
    period_end: date | None = None,
) -> pd.DataFrame:
    df = add_control_gap_score(df)
    df = add_fraud_flag_count(df)
    df = add_period_over_period_pct(df)
    df = add_vendor_concentration_pct(df)
    df = add_year_end_concentration(df, period_end=period_end)
    df = add_non_standard_pattern(df)
    return df


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def engineer_features(
    df: pd.DataFrame,
    period_end: date | None = None,
) -> pd.DataFrame:
    """Build the full Phase 2 feature set: T1 (for the ML matrix) + T2 (display
    + override fuel).

    `period_end` lets the auditor specify the period boundary explicitly for
    the year-end concentration feature. Defaults to max date in the data.
    """
    df = df.copy()
    df = _add_tier1_features(df)
    df = _add_tier2_features(df, period_end=period_end)
    return df


def get_feature_columns() -> list[str]:
    """Canonical T1 feature columns for the ML matrix (model.py)."""
    return list(FEATURE_COLS)


def get_t2_feature_columns() -> list[str]:
    """T2 feature columns — display + override fuel."""
    return list(T2_FEATURE_COLS)
