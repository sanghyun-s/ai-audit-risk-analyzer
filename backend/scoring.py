"""
scoring.py — ML output + materiality → final_tier + PCAOB labels + supporting columns.

This is the audit-logic layer that distinguishes App 3 from a generic ML
anomaly detector. It takes model.py's statistical output and applies the
materiality filter, producing the columns the user actually sees:

  * final_tier            — audit-adjusted tier after materiality
  * pcaob_label           — PCAOB-style label (Potential Material Weakness
                            Indicator / Potential Significant Deficiency /
                            Monitor — Below Escalation Threshold)
  * materiality_annotation — short human-readable explanation
  * active_flags          — semicolon-joined human-readable list of which
                            features fired for this row
  * flagged_status        — "Flagged" if final_tier in {High, Medium}, else
                            "Monitor"

Language rule: the labels use "Potential," "Indicator," "Monitor" throughout.
The app identifies risk indicators — it never issues audit conclusions.
"""
from __future__ import annotations

import pandas as pd

# Tier ordering for downgrade arithmetic. Higher index = more severe.
TIER_ORDER: list[str] = ["Monitor", "Low", "Medium", "High"]

# PCAOB-style label mapping. Note: "Low" and "Monitor" share a label —
# both mean below escalation threshold.
PCAOB_LABELS: dict[str, str] = {
    "High":    "Potential Material Weakness Indicator",
    "Medium":  "Potential Significant Deficiency",
    "Low":     "Monitor — Below Escalation Threshold",
    "Monitor": "Monitor — Below Escalation Threshold",
}

# Translate binary feature columns to human-readable labels for active_flags.
FLAG_LABELS: dict[str, str] = {
    "is_round_number":            "Round number amount",
    "is_weekend_posting":         "Weekend posting",
    "missing_description":        "Missing description",
    "is_new_vendor":              "New vendor",
    "is_near_approval_threshold": "Near approval threshold",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def downgrade_tier(tier: str, steps: int = 1) -> str:
    """Move down `steps` positions in TIER_ORDER, clamped to Monitor."""
    if tier not in TIER_ORDER:
        return "Monitor"
    idx = TIER_ORDER.index(tier)
    return TIER_ORDER[max(0, idx - steps)]


def apply_materiality_filter(
    row: pd.Series,
    performance_materiality: float,
    transaction_materiality: float,
) -> str:
    """Apply the materiality filter to one row's raw_tier.

    Logic per blueprint:
      amount >= transaction_materiality  → keep raw_tier
      amount >= performance_materiality  → downgrade one tier
      amount <  performance_materiality  → force Monitor
    """
    raw_tier = str(row.get("raw_tier", "Low"))
    amount = row.get("abs_amount", 0) or 0

    if amount >= transaction_materiality:
        return raw_tier
    if amount >= performance_materiality:
        return downgrade_tier(raw_tier, steps=1)
    return "Monitor"


def get_materiality_annotation(
    amount: float,
    performance_materiality: float,
    transaction_materiality: float,
) -> str:
    """One-line explanation of where this amount sits relative to thresholds."""
    if pd.isna(amount):
        amount = 0
    if amount >= transaction_materiality:
        return "Exceeds Transaction Materiality"
    if amount >= performance_materiality:
        return "Below Transaction Materiality"
    return "Below Performance Materiality"


def get_active_flags(row: pd.Series) -> str:
    """Build a semicolon-joined human-readable string of which features
    fired for this row. Used in the Streamlit table so users can see WHY
    a transaction was flagged, not just THAT it was."""
    flags: list[str] = []

    # Z-score: |z| >= 2.0 is the conventional "unusual" threshold.
    z = row.get("amount_zscore_by_account", 0)
    try:
        if abs(float(z)) >= 2.0:
            flags.append("Unusual amount for account")
    except (TypeError, ValueError):
        pass

    for col, label in FLAG_LABELS.items():
        try:
            if int(row.get(col, 0) or 0) == 1:
                flags.append(label)
        except (TypeError, ValueError):
            continue

    return "; ".join(flags) if flags else "Statistical anomaly only"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def apply_scoring(
    df: pd.DataFrame,
    fs_materiality: float,
    performance_materiality: float,
    transaction_materiality: float,
) -> pd.DataFrame:
    """Apply the audit-logic layer to a dataframe that already has model.py
    output (anomaly_score, raw_tier). Adds:
      final_tier, pcaob_label, materiality_annotation, active_flags,
      flagged_status.

    `fs_materiality` is accepted for API symmetry / future use even though
    the filter logic uses only performance and transaction thresholds.
    """
    del fs_materiality  # explicitly unused in MVP filter logic
    df = df.copy()

    df["final_tier"] = df.apply(
        lambda row: apply_materiality_filter(
            row, performance_materiality, transaction_materiality
        ),
        axis=1,
    )
    df["pcaob_label"] = df["final_tier"].map(PCAOB_LABELS).fillna(
        "Monitor — Below Escalation Threshold"
    )
    df["materiality_annotation"] = df["abs_amount"].apply(
        lambda amt: get_materiality_annotation(
            amt, performance_materiality, transaction_materiality
        )
    )
    df["active_flags"] = df.apply(get_active_flags, axis=1)
    df["flagged_status"] = df["final_tier"].apply(
        lambda x: "Flagged" if x in ("High", "Medium") else "Monitor"
    )

    return df
