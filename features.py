"""
features.py — raw GL CSV → cleaned dataframe + 6 engineered feature columns.

This module is the data-cleaning and feature-engineering layer of App 3.
The model layer (model.py) consumes the output of `engineer_features`.

MVP feature set (Tier 1):
  * amount_zscore_by_account  — account-level magnitude outlier
  * is_round_number           — manual entry / estimate fraud indicator
  * is_weekend_posting        — unusual posting timing
  * missing_description       — documentation control gap
  * is_new_vendor             — vendor appears < 3 times in dataset
  * is_near_approval_threshold — within 5% below $5K / $10K / $25K

Each maps to a specific audit-theory source — see the blueprint feature
reference table.
"""
from __future__ import annotations

import pandas as pd


# ---- Required GL columns for Phase 1 ----
REQUIRED_COLUMNS: list[str] = [
    "date",
    "amount",
    "account_code",
    "account_name",
    "vendor",
    "description",
    "journal_ref",
]

# Common approval thresholds — invoice-splitting / limit-test indicators
APPROVAL_THRESHOLDS: list[int] = [5000, 10000, 25000]

# Feature column list — consumed by model.py for the feature matrix X
FEATURE_COLS: list[str] = [
    "amount_zscore_by_account",
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
    """Return (ok, missing_columns). Fails fast so the UI can show a clear error."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    return (len(missing) == 0, missing)


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------

def clean_gl_data(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce dtypes and add abs_amount. Returns a new dataframe — does not
    mutate input. Rows with unparseable date or amount are kept (NaT/NaN
    propagates) so the caller can decide how to handle them; for MVP we
    assume well-formed input from the sample CSV.
    """
    df = df.copy()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["abs_amount"] = df["amount"].abs()

    # Normalize text fields for downstream use
    for col in ("vendor", "description", "account_name", "account_code"):
        if col in df.columns:
            df[col] = df[col].astype("string")

    return df


# ---------------------------------------------------------------------------
# Individual feature functions
# ---------------------------------------------------------------------------

def _is_round_number(amount: float) -> int:
    if pd.isna(amount):
        return 0
    return int(abs(amount) % 100 == 0)


def _near_approval_threshold(amount: float) -> int:
    """1 if amount is within 5% below any common approval threshold."""
    if pd.isna(amount):
        return 0
    amount = abs(amount)
    for threshold in APPROVAL_THRESHOLDS:
        if threshold * 0.95 <= amount < threshold:
            return 1
    return 0


def _amount_zscore_by_account(df: pd.DataFrame) -> pd.Series:
    """Account-level z-score of abs_amount. Returns 0.0 for accounts with
    only one transaction (or zero variance) to avoid NaN propagation."""
    def _z(group: pd.Series) -> pd.Series:
        std = group.std(ddof=0)
        if std == 0 or pd.isna(std):
            return pd.Series(0.0, index=group.index)
        return (group - group.mean()) / std

    return (
        df.groupby("account_name", group_keys=False)["abs_amount"]
          .apply(_z)
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Take a cleaned GL dataframe and return it with the 6 MVP feature columns
    appended. Assumes `clean_gl_data` has already been applied."""
    df = df.copy()

    # 1. Account-level magnitude z-score
    df["amount_zscore_by_account"] = _amount_zscore_by_account(df)

    # 2. Round number flag
    df["is_round_number"] = df["abs_amount"].apply(_is_round_number).astype(int)

    # 3. Weekend posting flag (Saturday=5, Sunday=6)
    df["is_weekend_posting"] = (
        df["date"].dt.weekday.isin([5, 6]).astype(int)
    )

    # 4. Missing description (null or empty/whitespace string)
    df["missing_description"] = (
        df["description"].isna()
        | (df["description"].astype(str).str.strip() == "")
        | (df["description"].astype(str).str.strip().str.lower() == "nan")
    ).astype(int)

    # 5. New vendor — appears fewer than 3 times in the full dataset
    vendor_counts = df["vendor"].fillna("UNKNOWN").value_counts()
    df["vendor_txn_count"] = df["vendor"].fillna("UNKNOWN").map(vendor_counts)
    df["is_new_vendor"] = (df["vendor_txn_count"] < 3).astype(int)

    # 6. Near approval threshold
    df["is_near_approval_threshold"] = (
        df["abs_amount"].apply(_near_approval_threshold).astype(int)
    )

    return df


def get_feature_columns() -> list[str]:
    """Returns the canonical list of feature columns for model.py."""
    return list(FEATURE_COLS)
