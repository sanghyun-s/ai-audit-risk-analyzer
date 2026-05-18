"""
generate_sample_gl.py — produces sample_data/sample_gl.csv

Phase 2 schema. Simulates a 2,000-row QuickBooks-style General Ledger for a
small private for-profit entity. Generates baseline transactions plus salted-in
anomalies that should trigger:

  T1 features:
    * is_round_number
    * is_weekend_posting
    * missing_description
    * is_new_vendor
    * is_near_approval_threshold
    * amount_zscore_by_account (account-level outliers)

  T2 features (Phase 2):
    * control_gap_score        — composite (missing_desc + weekend)
    * fraud_flag_count         — count of fraud-indicator flags fired
    * fraud_risk_flag          — fraud_flag_count >= 2
    * period_over_period_pct   — account % change vs prior month
    * vendor_concentration_pct — vendor share of total disbursements
    * is_year_end_concentration — posted in last 10 days of period
    * is_non_standard_pattern  — debit/credit pairing outside the 6 standards

Phase 2 schema additions over Phase 1:
  * debit_amount   — for debit-natural accounts, holds the transaction amount
  * credit_amount  — for credit-natural accounts, holds the transaction amount
  * dr_cr_pattern  — one of 6 standard pattern names or "non_standard"

Run once:  python generate_sample_gl.py
Output:    sample_data/sample_gl.csv
"""
from __future__ import annotations

import os
import random
from datetime import date, timedelta

import numpy as np
import pandas as pd

# ---- Reproducibility ----
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# ---- Configuration ----
N_ROWS = 2000
START_DATE = date(2024, 1, 1)
END_DATE = date(2024, 12, 31)
OUT_PATH = os.path.join("sample_data", "sample_gl.csv")

# Chart of accounts — code, name, mean, sd, natural balance side ("D" or "C")
ACCOUNTS = [
    ("4000", "Sales Revenue",            5000, 2500, "C"),
    ("4100", "Service Revenue",          3500, 1800, "C"),
    ("5000", "Cost of Goods Sold",       2800, 1500, "D"),
    ("5100", "Inventory Purchases",      4200, 2200, "D"),
    ("6000", "Salaries Expense",         6500, 1200, "D"),
    ("6010", "Payroll Tax Expense",       950,  300, "D"),
    ("6100", "Rent Expense",             3000,  100, "D"),
    ("6200", "Utilities Expense",         450,  150, "D"),
    ("6300", "Office Supplies",           280,  180, "D"),
    ("6400", "Professional Fees",        1800, 1100, "D"),
    ("6500", "Travel & Entertainment",    620,  400, "D"),
    ("6600", "Marketing Expense",        1200,  700, "D"),
    ("6700", "Software Subscriptions",    380,  140, "D"),
    ("6800", "Insurance Expense",        1100,  120, "D"),
    ("6900", "Repairs & Maintenance",     520,  380, "D"),
    ("7000", "Cash Disbursements",       2200, 1800, "D"),
    ("1200", "Accounts Receivable",      4800, 2400, "D"),
    ("2000", "Accounts Payable",         3100, 1900, "C"),
]

# Account codes that are PART OF a standard debit/credit pairing — touching
# any of these is considered a "standard pattern" row.
STANDARD_PATTERN_CODES = {"1200", "2000", "4000", "4100", "5100",
                          "6000", "6010", "6400", "7000"}

# Established vendors — these should appear many times (>=3)
ESTABLISHED_VENDORS = [
    "Acme Supplies Inc",     "Pacific Office Co",   "Bayview Logistics",
    "Northstar Utilities",   "Greenline Insurance", "Apex Payroll Services",
    "Citywide Rentals LLC",  "Vector IT Solutions", "Summit Marketing Group",
    "Bridgepoint Travel",    "Quantum Software Inc","Reliant Repair Services",
    "Customer A Corp",       "Customer B LLC",      "Customer C Holdings",
    "Customer D Industries", "Standard Bank",
]

# One-off vendor name bases — each anomaly gets a unique suffix
NEW_VENDORS = [
    "QuickFix Consultants",  "Maple Holdings Ltd",  "Echo Services",
    "Vista Trading Co",      "Pinecone Partners",   "Redrock LLC",
    "Brightway Group",
]

DESCRIPTIONS = [
    "Monthly invoice", "Vendor payment", "Routine purchase",
    "Service rendered", "Supplies order", "Reimbursement",
    "Recurring charge", "Equipment lease", "Subscription renewal",
]

# Accounts that get a deliberate period-over-period spike, and which month.
# Used to seed something dramatic for period_over_period_pct.
POP_SPIKE_PLAN = {
    "Marketing Expense":      (8,  3.5),   # Aug spike
    "Professional Fees":      (11, 4.0),   # Nov spike
    "Travel & Entertainment": (6,  2.8),   # Jun spike
}


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def random_business_date() -> date:
    total_days = (END_DATE - START_DATE).days
    d = START_DATE + timedelta(days=random.randint(0, total_days))
    if d.weekday() >= 5 and random.random() < 0.90:
        d = START_DATE + timedelta(days=random.randint(0, total_days))
    return d


def random_weekend_date() -> date:
    total_days = (END_DATE - START_DATE).days
    while True:
        d = START_DATE + timedelta(days=random.randint(0, total_days))
        if d.weekday() >= 5:
            return d


def random_date_in_month(month: int) -> date:
    if month == 12:
        next_month = date(2025, 1, 1)
    else:
        next_month = date(2024, month + 1, 1)
    days_in_month = (next_month - date(2024, month, 1)).days
    while True:
        d = date(2024, month, random.randint(1, days_in_month))
        if d.weekday() < 5:
            return d


def random_year_end_date() -> date:
    """A date in the last 10 days of the period."""
    return END_DATE - timedelta(days=random.randint(0, 9))


# ---------------------------------------------------------------------------
# Row helpers
# ---------------------------------------------------------------------------

def split_debit_credit(amount: float, side: str) -> tuple[float, float]:
    """Place the full amount on the natural side. The flat one-leg view used
    by QuickBooks-style GL exports."""
    amt = abs(round(amount, 2))
    return (amt, 0.0) if side == "D" else (0.0, amt)


def standard_or_not(account_code: str) -> str:
    return "standard" if account_code in STANDARD_PATTERN_CODES else "non_standard"


def make_baseline_row(i: int) -> dict:
    code, name, mu, sd, side = random.choice(ACCOUNTS)
    raw_amt = max(50.0, np.random.normal(mu, sd))
    amt = round(raw_amt, 2)
    if amt % 100 == 0:
        amt += round(random.uniform(0.13, 7.77), 2)
    debit, credit = split_debit_credit(amt, side)
    return {
        "date": random_business_date().isoformat(),
        "amount": amt,
        "debit_amount": debit,
        "credit_amount": credit,
        "account_code": code,
        "account_name": name,
        "vendor": random.choice(ESTABLISHED_VENDORS),
        "description": random.choice(DESCRIPTIONS),
        "journal_ref": f"JE-{10000 + i}",
        "dr_cr_pattern": standard_or_not(code),
    }


def make_pop_spike_row(i: int, account_name: str, month: int) -> dict:
    code, name, mu, sd, side = next(a for a in ACCOUNTS if a[1] == account_name)
    raw_amt = max(50.0, np.random.normal(mu, sd))
    amt = round(raw_amt, 2)
    if amt % 100 == 0:
        amt += round(random.uniform(0.13, 7.77), 2)
    debit, credit = split_debit_credit(amt, side)
    return {
        "date": random_date_in_month(month).isoformat(),
        "amount": amt,
        "debit_amount": debit,
        "credit_amount": credit,
        "account_code": code,
        "account_name": name,
        "vendor": random.choice(ESTABLISHED_VENDORS),
        "description": random.choice(DESCRIPTIONS),
        "journal_ref": f"JE-{10000 + i}",
        "dr_cr_pattern": standard_or_not(code),
    }


def unique_new_vendor(i: int) -> str:
    base = random.choice(NEW_VENDORS)
    return f"{base} #{i:04d}"


def inject_anomaly(row: dict, kind: str, i: int) -> dict:
    """Mutate a baseline row to plant a specific anomaly type."""
    if kind == "round_number":
        row["amount"] = float(random.choice([500, 1000, 2500, 5000, 7500, 10000]))
    elif kind == "weekend":
        row["date"] = random_weekend_date().isoformat()
    elif kind == "missing_desc":
        row["description"] = random.choice(["", None])
    elif kind == "new_vendor":
        row["vendor"] = unique_new_vendor(i)
    elif kind == "near_threshold":
        base = random.choice([5000, 10000, 25000])
        row["amount"] = round(base * random.uniform(0.951, 0.999), 2)
    elif kind == "account_outlier":
        code = row["account_code"]
        _, _, mu, sd, _ = next(a for a in ACCOUNTS if a[0] == code)
        row["amount"] = round(mu + (sd * random.uniform(5.0, 8.0)), 2)
    elif kind == "year_end":
        row["date"] = random_year_end_date().isoformat()
    elif kind == "non_standard_dr_cr":
        row["dr_cr_pattern"] = "non_standard"
    elif kind == "stacked":
        # Hero demo row — fires many flags at once
        row["date"] = random_weekend_date().isoformat()
        row["vendor"] = unique_new_vendor(i)
        row["amount"] = float(random.choice([4850.0, 9850.0, 24850.0]))
        row["description"] = ""

    # Recompute debit/credit because amount may have changed
    code = row["account_code"]
    _, _, _, _, side = next(a for a in ACCOUNTS if a[0] == code)
    debit, credit = split_debit_credit(row["amount"], side)
    row["debit_amount"] = debit
    row["credit_amount"] = credit
    return row


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    rows: list[dict] = []

    # 1. Baseline (88%)
    n_baseline = int(N_ROWS * 0.88)
    for i in range(n_baseline):
        rows.append(make_baseline_row(i))

    # 2. Period-over-period spikes
    pop_rows = []
    pop_start = n_baseline
    for account_name, (month, multiplier) in POP_SPIKE_PLAN.items():
        n_spikes = int(8 * multiplier)
        for j in range(n_spikes):
            pop_rows.append(make_pop_spike_row(
                pop_start + len(pop_rows), account_name, month))
    rows.extend(pop_rows)

    # 3. Anomalies for the rest
    used = len(rows)
    remaining = N_ROWS - used
    anomaly_plan = (
        ["round_number"]         * int(remaining * 0.13)
        + ["weekend"]            * int(remaining * 0.13)
        + ["missing_desc"]       * int(remaining * 0.13)
        + ["new_vendor"]         * int(remaining * 0.13)
        + ["near_threshold"]     * int(remaining * 0.13)
        + ["account_outlier"]    * int(remaining * 0.08)
        + ["year_end"]           * int(remaining * 0.10)
        + ["non_standard_dr_cr"] * int(remaining * 0.10)
        + ["stacked"]            * int(remaining * 0.07)
    )
    while len(anomaly_plan) < remaining:
        anomaly_plan.append(random.choice(
            ["round_number", "weekend", "missing_desc", "new_vendor",
             "near_threshold", "year_end", "non_standard_dr_cr"]
        ))

    for i, kind in enumerate(anomaly_plan):
        base = make_baseline_row(used + i)
        rows.append(inject_anomaly(base, kind, used + i))

    # 4. Assemble + shuffle
    df = pd.DataFrame(rows)
    df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)
    df["journal_ref"] = [f"JE-{10000 + i}" for i in range(len(df))]

    df = df[["date", "amount", "debit_amount", "credit_amount",
             "account_code", "account_name",
             "vendor", "description", "journal_ref", "dr_cr_pattern"]]

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(df)} rows to {OUT_PATH}")
    print(df.head(5).to_string(index=False))
    print()
    print("dr_cr_pattern distribution:")
    print(df["dr_cr_pattern"].value_counts().to_string())


if __name__ == "__main__":
    main()
