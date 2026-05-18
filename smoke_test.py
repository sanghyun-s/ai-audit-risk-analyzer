"""
smoke_test.py — runs the full Phase 1 pipeline on sample_gl.csv and verifies
that the Phase 1 done-criteria (12 items from the phase plan) are satisfied.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# Make sure we import from the project root, not site-packages
sys.path.insert(0, str(Path(__file__).parent))

from features import (
    REQUIRED_COLUMNS,
    clean_gl_data,
    engineer_features,
    get_feature_columns,
    validate_required_columns,
)
from model import SENSITIVITY_MAP, run_isolation_forest
from scoring import apply_scoring


def check(label: str, ok: bool, detail: str = "") -> None:
    mark = "✓" if ok else "✗"
    print(f"  {mark} {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        raise AssertionError(label)


def main() -> None:
    print("Running Phase 1 smoke test on sample_gl.csv\n")

    # ---- 1. CSV read ----
    raw = pd.read_csv("sample_data/sample_gl.csv")
    check("CSV loads", len(raw) > 0, f"{len(raw):,} rows")

    # ---- 2. Column validation ----
    ok, missing = validate_required_columns(raw)
    check("Required columns present", ok, f"missing: {missing}")

    # ---- 3. Cleaning ----
    cleaned = clean_gl_data(raw)
    check("date converted to datetime",
          pd.api.types.is_datetime64_any_dtype(cleaned["date"]))
    check("amount is numeric",
          pd.api.types.is_numeric_dtype(cleaned["amount"]))
    check("abs_amount created", "abs_amount" in cleaned.columns)

    # ---- 4. Feature engineering ----
    feat = engineer_features(cleaned)
    feature_cols = get_feature_columns()
    for col in feature_cols:
        check(f"feature '{col}' computed",
              col in feat.columns and feat[col].notna().any())

    print(f"\n  Feature firing summary:")
    for col in feature_cols[1:]:  # skip z-score (continuous)
        print(f"    {col:32s} → {int(feat[col].sum()):>4d} of {len(feat):,}")

    # ---- 5. Entity / materiality inputs (mimicking app.py) ----
    entity_type = "Private for-profit"
    benchmark_figure = 150_000.0
    fs_pct = 0.04
    fs_mat = benchmark_figure * fs_pct
    perf_mat = fs_mat * 0.50
    txn_mat = fs_mat * 0.80
    print(f"\n  Materiality (Private for-profit, EBT=$150,000):")
    print(f"    FS materiality          ${fs_mat:>9,.0f}")
    print(f"    Performance materiality ${perf_mat:>9,.0f}")
    print(f"    Transaction materiality ${txn_mat:>9,.0f}")

    # ---- 6. ML scoring ----
    sensitivity = "Balanced (0.05)"
    check("sensitivity maps to contamination",
          SENSITIVITY_MAP[sensitivity] == 0.05)
    scored = run_isolation_forest(feat, feature_cols, sensitivity)
    check("anomaly_score present", "anomaly_score" in scored.columns)
    check("raw_tier present", "raw_tier" in scored.columns)
    check("scores sorted ascending (most anomalous first)",
          scored["anomaly_score"].iloc[0] <= scored["anomaly_score"].iloc[-1])

    raw_tier_counts = scored["raw_tier"].value_counts().to_dict()
    print(f"\n  raw_tier distribution: {raw_tier_counts}")

    # ---- 7. Audit-logic scoring ----
    final = apply_scoring(scored, fs_mat, perf_mat, txn_mat)
    for col in ("final_tier", "pcaob_label", "materiality_annotation",
                "active_flags", "flagged_status"):
        check(f"column '{col}' added", col in final.columns)

    final_tier_counts = final["final_tier"].value_counts().to_dict()
    print(f"\n  final_tier distribution: {final_tier_counts}")

    pcaob_counts = final["pcaob_label"].value_counts().to_dict()
    print(f"\n  PCAOB label distribution:")
    for k, v in pcaob_counts.items():
        print(f"    {v:>4d}  {k}")

    # ---- 8. Verify materiality filter actually downgrades small amounts ----
    small_high = final[
        (final["raw_tier"] == "High")
        & (final["abs_amount"] < perf_mat)
    ]
    if len(small_high):
        all_monitor = (small_high["final_tier"] == "Monitor").all()
        check(f"small-amount High-tier rows ({len(small_high)}) downgraded to Monitor",
              all_monitor)

    # ---- 9. raw_tier and final_tier are distinct columns ----
    check("raw_tier and final_tier remain distinct",
          "raw_tier" in final.columns and "final_tier" in final.columns)

    # ---- 10. PCAOB labels use hedged language ----
    pcaob_text = " ".join(final["pcaob_label"].unique())
    forbidden = ["fraud occurred", "is fraudulent", "material weakness exists",
                 "violation"]
    bad = [w for w in forbidden if w.lower() in pcaob_text.lower()]
    check("PCAOB labels use Potential/Indicator/Monitor language", not bad,
          f"forbidden found: {bad}" if bad else "")

    # ---- 11. Active flags column is human-readable ----
    sample_flags = final["active_flags"].iloc[0]
    check("active_flags is a readable string", isinstance(sample_flags, str))
    print(f"\n  Sample active_flags row 0: {sample_flags!r}")

    # ---- 12. Show top 3 flagged transactions ----
    flagged = final[final["flagged_status"] == "Flagged"]
    print(f"\n  Flagged: {len(flagged)} of {len(final)} "
          f"({len(flagged)/len(final)*100:.1f}%)")
    print(f"\n  Top 3 flagged transactions:")
    show_cols = ["date", "account_name", "vendor", "amount",
                 "anomaly_score", "final_tier", "pcaob_label", "active_flags"]
    print(flagged[show_cols].head(3).to_string(index=False))

    print("\nAll Phase 1 done-criteria pass.")


if __name__ == "__main__":
    main()
