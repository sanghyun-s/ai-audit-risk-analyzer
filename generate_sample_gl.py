"""
generate_sample_gl.py — produces sample_data/sample_gl.csv

Simulates a 2,000-row QuickBooks-style General Ledger for a small private
for-profit entity. Generates realistic baseline transactions plus a salted-in
minority of audit-relevant anomalies that should trigger the 6 MVP features:

  * is_round_number
  * is_weekend_posting
  * missing_description
  * is_new_vendor
  * is_near_approval_threshold
  * amount_zscore_by_account (account-level outliers)

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

# Chart of accounts — code + name + typical magnitude range
# Mapped roughly to audit cycles (Sales, Purchases, Payroll, Other)
ACCOUNTS = [
    # code, name, mean_amount, sd_amount
    ("4000", "Sales Revenue",            5000, 2500),
    ("4100", "Service Revenue",          3500, 1800),
    ("5000", "Cost of Goods Sold",       2800, 1500),
    ("5100", "Inventory Purchases",      4200, 2200),
    ("6000", "Salaries Expense",         6500, 1200),
    ("6010", "Payroll Tax Expense",       950,  300),
    ("6100", "Rent Expense",             3000,  100),   # fixed-ish
    ("6200", "Utilities Expense",         450,  150),
    ("6300", "Office Supplies",           280,  180),
    ("6400", "Professional Fees",        1800, 1100),
    ("6500", "Travel & Entertainment",    620,  400),
    ("6600", "Marketing Expense",        1200,  700),
    ("6700", "Software Subscriptions",    380,  140),
    ("6800", "Insurance Expense",        1100,  120),
    ("6900", "Repairs & Maintenance",     520,  380),
    ("7000", "Cash Disbursements",       2200, 1800),
    ("1200", "Accounts Receivable",      4800, 2400),
    ("2000", "Accounts Payable",         3100, 1900),
]

# Established vendor pool — these should appear many times
ESTABLISHED_VENDORS = [
    "Acme Supplies Inc",     "Pacific Office Co",   "Bayview Logistics",
    "Northstar Utilities",   "Greenline Insurance", "Apex Payroll Services",
    "Citywide Rentals LLC",  "Vector IT Solutions", "Summit Marketing Group",
    "Bridgepoint Travel",    "Quantum Software Inc","Reliant Repair Services",
    "Customer A Corp",       "Customer B LLC",      "Customer C Holdings",
    "Customer D Industries", "Standard Bank",
]

# One-off / new vendors — appear <3 times → trigger is_new_vendor
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


def random_business_date() -> date:
    """Date weighted toward weekdays. Returns a date in [START_DATE, END_DATE]."""
    total_days = (END_DATE - START_DATE).days
    d = START_DATE + timedelta(days=random.randint(0, total_days))
    # 90% chance to re-roll if weekend (to make weekend posts a true minority)
    if d.weekday() >= 5 and random.random() < 0.90:
        d = START_DATE + timedelta(days=random.randint(0, total_days))
    return d


def random_weekend_date() -> date:
    """Returns a Saturday or Sunday in range."""
    total_days = (END_DATE - START_DATE).days
    while True:
        d = START_DATE + timedelta(days=random.randint(0, total_days))
        if d.weekday() >= 5:
            return d


def make_baseline_row(i: int) -> dict:
    code, name, mu, sd = random.choice(ACCOUNTS)
    # Most rows: normal-ish, non-round, established vendor, with description
    raw_amt = max(50.0, np.random.normal(mu, sd))
    amt = round(raw_amt, 2)
    # Avoid accidentally landing on round/threshold values
    if amt % 100 == 0:
        amt += round(random.uniform(0.13, 7.77), 2)
    vendor = random.choice(ESTABLISHED_VENDORS)
    description = random.choice(DESCRIPTIONS)
    return {
        "date": random_business_date().isoformat(),
        "amount": amt,
        "account_code": code,
        "account_name": name,
        "vendor": vendor,
        "description": description,
        "journal_ref": f"JE-{10000 + i}",
    }


def unique_new_vendor(i: int) -> str:
    """Build a unique one-off vendor name per anomaly row so it appears
    fewer than 3 times in the dataset (triggering is_new_vendor)."""
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
        # 5% below $5K / $10K / $25K
        base = random.choice([5000, 10000, 25000])
        row["amount"] = round(base * random.uniform(0.951, 0.999), 2)
    elif kind == "account_outlier":
        # Amount well above typical for that account
        code = row["account_code"]
        acct = next(a for a in ACCOUNTS if a[0] == code)
        _, _, mu, sd = acct
        row["amount"] = round(mu + (sd * random.uniform(5.0, 8.0)), 2)
    elif kind == "stacked":
        # Multiple flags at once → should trigger qualitative override in Phase 3 T2
        row["date"] = random_weekend_date().isoformat()
        row["vendor"] = unique_new_vendor(i)
        row["amount"] = float(random.choice([4850.0, 9850.0, 24850.0]))
        row["description"] = ""
    return row


def main() -> None:
    rows = []

    # ~92% baseline — these will generally NOT trigger flags
    n_baseline = int(N_ROWS * 0.92)
    for i in range(n_baseline):
        rows.append(make_baseline_row(i))

    # ~8% anomalies — distributed across types
    remaining = N_ROWS - n_baseline
    anomaly_plan = (
        ["round_number"]     * int(remaining * 0.20)
        + ["weekend"]        * int(remaining * 0.15)
        + ["missing_desc"]   * int(remaining * 0.15)
        + ["new_vendor"]     * int(remaining * 0.15)
        + ["near_threshold"] * int(remaining * 0.15)
        + ["account_outlier"] * int(remaining * 0.10)
        + ["stacked"]        * int(remaining * 0.10)
    )
    # Pad to exactly `remaining` with random picks
    while len(anomaly_plan) < remaining:
        anomaly_plan.append(random.choice(
            ["round_number", "weekend", "missing_desc", "new_vendor", "near_threshold"]
        ))

    for i, kind in enumerate(anomaly_plan):
        base = make_baseline_row(n_baseline + i)
        rows.append(inject_anomaly(base, kind, n_baseline + i))

    df = pd.DataFrame(rows)

    # Shuffle so anomalies aren't clustered at the end
    df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)

    # Re-number journal_ref in order after shuffle for realism
    df["journal_ref"] = [f"JE-{10000 + i}" for i in range(len(df))]

    # Final column order matches blueprint spec
    df = df[["date", "amount", "account_code", "account_name",
             "vendor", "description", "journal_ref"]]

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(df)} rows to {OUT_PATH}")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
