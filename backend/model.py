"""
model.py — feature matrix → anomaly_score + raw_tier.

This is the ML layer of App 3. Single responsibility: answer "is this
transaction statistically unusual?" Produces two columns:

  * anomaly_score (float) — Isolation Forest decision_function output.
    Lower = more anomalous. NOT the final audit tier.
  * raw_tier (High/Medium/Low) — bucketed anomaly score. NOT the final
    audit tier either — scoring.py applies the materiality filter to
    produce final_tier.

Keeping `raw_tier` and `final_tier` as distinct columns is what makes App 3
an audit analytics tool rather than a generic ML anomaly detector.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# Detection sensitivity → Isolation Forest contamination parameter.
# In audit terms, this is the auditor-controlled Detection Risk dial.
SENSITIVITY_MAP: dict[str, float] = {
    "Conservative (0.03)": 0.03,
    "Balanced (0.05)":     0.05,
    "Aggressive (0.10)":   0.10,
}

# Default starting bin edges for raw_tier. Adjust after testing with real
# sample GL data if the distribution skews too far in either direction.
RAW_TIER_BINS: list[float] = [-np.inf, -0.15, -0.05, np.inf]
RAW_TIER_LABELS: list[str] = ["High", "Medium", "Low"]


def run_isolation_forest(
    df: pd.DataFrame,
    feature_cols: list[str],
    detection_sensitivity: str,
    random_state: int = 42,
) -> pd.DataFrame:
    """Fit IsolationForest on df[feature_cols], add anomaly_score and raw_tier.

    Args:
        df: DataFrame already cleaned and feature-engineered.
        feature_cols: Column names to use as the feature matrix.
        detection_sensitivity: One of the keys in SENSITIVITY_MAP.
        random_state: For reproducible scores.

    Returns:
        DataFrame with `anomaly_score`, `anomaly_label`, and `raw_tier`
        columns added. Sorted ascending by anomaly_score so the most
        anomalous rows appear at the top.
    """
    if detection_sensitivity not in SENSITIVITY_MAP:
        raise ValueError(
            f"Unknown detection_sensitivity {detection_sensitivity!r}. "
            f"Expected one of {list(SENSITIVITY_MAP)}."
        )
    contamination = SENSITIVITY_MAP[detection_sensitivity]

    df = df.copy()

    # Feature matrix — fillna(0) is safe because all 6 features are either
    # binary flags or z-scores (where 0 = average).
    X = df[feature_cols].fillna(0).values

    # StandardScaler is non-negotiable — without it the (dollar-scale)
    # z-score feature dominates the binary flags in the tree splits.
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=random_state,
    )
    model.fit(X_scaled)

    # decision_function: continuous score. Lower = more anomalous.
    df["anomaly_score"] = model.decision_function(X_scaled)
    # predict: -1 anomaly, 1 normal. Useful for debugging and Tier-2 flags.
    df["anomaly_label"] = model.predict(X_scaled)

    # Bucket the continuous score into a coarse raw tier.
    df["raw_tier"] = pd.cut(
        df["anomaly_score"],
        bins=RAW_TIER_BINS,
        labels=RAW_TIER_LABELS,
    ).astype(str)

    # Sort ascending so the most-anomalous rows are first.
    df = df.sort_values("anomaly_score", ascending=True).reset_index(drop=True)

    return df
