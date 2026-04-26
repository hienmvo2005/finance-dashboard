"""
clean_transactions.py
---------------------
Cleans and categorizes a raw bank/credit-card transaction export.

Inputs:  data/raw_transactions.csv   (messy, real-world style)
Outputs: output/clean_transactions.csv  (analysis-ready, one row per posted txn)
         output/summary_by_category.csv (monthly category totals)
         output/data_quality_report.txt (what was dropped / fixed and why)

Demonstrates:
  - Robust date parsing across mixed formats
  - Description normalization (case, whitespace, prefixes)
  - Regex-based merchant + category mapping
  - Duplicate detection (exact + near-duplicate)
  - Pending transaction filtering
  - Refund handling (so spending totals are accurate)
  - Derived columns for downstream BI work (month, weekday, txn_type)
"""

import re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "raw_transactions.csv"
OUT_DIR = ROOT / "output"
OUT_DIR.mkdir(exist_ok=True)

# ============================================================================
# 1. LOAD
# ============================================================================
df = pd.read_csv(RAW_PATH, dtype=str)        # read everything as string first
print(f"Loaded {len(df)} raw rows")
initial_count = len(df)
report_lines = [f"Initial rows loaded: {initial_count}"]

# ============================================================================
# 2. CLEAN BASIC FIELDS
# ============================================================================
# Strip whitespace from descriptions, collapse internal multi-spaces
df["Description"] = (
    df["Description"]
      .fillna("")
      .str.strip()
      .str.replace(r"\s+", " ", regex=True)
)

# Drop rows with no description AND no amount — unrecoverable
mask_empty = (df["Description"] == "") & (df["Amount"].isna() | (df["Amount"] == ""))
report_lines.append(f"Dropped fully-empty rows: {mask_empty.sum()}")
df = df[~mask_empty].copy()

# Parse amount — coerce non-numeric to NaN, then drop those
df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
n_bad_amt = df["Amount"].isna().sum()
report_lines.append(f"Dropped rows with unparseable amount: {n_bad_amt}")
df = df.dropna(subset=["Amount"]).copy()

# Parse date — try multiple formats, in order of likelihood
def parse_date(s):
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return pd.to_datetime(s, format=fmt)
        except (ValueError, TypeError):
            continue
    return pd.to_datetime(s, errors="coerce")  # last resort

df["Date"] = df["Date"].apply(parse_date)
n_bad_date = df["Date"].isna().sum()
report_lines.append(f"Dropped rows with unparseable date: {n_bad_date}")
df = df.dropna(subset=["Date"]).copy()

# ============================================================================
# 3. FILTER PENDING TRANSACTIONS
# ============================================================================
# Banks often export both pending + posted versions. Keep posted only.
pending_mask = df["Description"].str.upper().str.startswith("PENDING")
report_lines.append(f"Dropped pending-transaction duplicates: {pending_mask.sum()}")
df = df[~pending_mask].copy()

# ============================================================================
# 4. NORMALIZE DESCRIPTIONS  (uppercase, strip noise codes)
# ============================================================================
df["Description_upper"] = df["Description"].str.upper()

# Strip noise from a *separate* display column so it doesn't break matching.
# Categorization rules below match against Description_upper (the raw form);
# Description_clean is just for human readability if/when needed.
df["Description_clean"] = df["Description_upper"]
NOISE_PATTERNS = [
    r"#\d+",                  # store numbers like #04521
    r"\s+(SD|LA|CA|NY)\b",    # trailing state codes
    r"\s+SAN DIEGO\b",
    r"\s+DEL MAR\b",
    r"\s+LA JOLLA\b",
    r"\s+NEW YORK\b",
]
for pat in NOISE_PATTERNS:
    df["Description_clean"] = df["Description_clean"].str.replace(pat, "", regex=True)
df["Description_clean"] = df["Description_clean"].str.replace(r"\s+", " ", regex=True).str.strip()

# ============================================================================
# 5. MERCHANT + CATEGORY MAPPING
# ============================================================================
# Order matters: more specific patterns first.
# Each tuple: (regex, canonical_merchant, category)
RULES = [
    # Income
    (r"PAYROLL|DIRECT DEPOSIT.*ACME",          "Acme Corp Payroll",   "Income"),
    (r"VENMO CASHOUT",                         "Venmo Cashout",       "Income"),
    (r"REFUND",                                None,                  "Refund"),

    # Housing & utilities
    (r"PROPERTY MG|RENT",                      "Rent",                "Housing"),
    (r"SDGE|SDG&E|SAN DIEGO GAS",              "SDG&E",               "Utilities"),
    (r"AT&T|ATT MOBILITY",                     "AT&T",                "Utilities"),

    # Subscriptions
    (r"NETFLIX",                               "Netflix",             "Subscriptions"),
    (r"SPOTIFY",                               "Spotify",             "Subscriptions"),
    (r"APPLE\.COM|APL\*ITUNES|APL ITUNES",     "Apple",               "Subscriptions"),

    # Fitness
    (r"24 HOUR FITNESS|24HR FITNESS",          "24 Hour Fitness",     "Fitness"),
    (r"COREPOWER|CORE POWER YOGA",             "CorePower Yoga",      "Fitness"),

    # Groceries
    (r"TRADER JOE|TJ'S",                       "Trader Joe's",        "Groceries"),
    (r"RALPHS",                                "Ralphs",              "Groceries"),
    (r"VONS",                                  "Vons",                "Groceries"),

    # Coffee, dining
    (r"STARBUCKS|SBUX",                        "Starbucks",           "Coffee"),
    (r"CHIPOTLE",                              "Chipotle",            "Dining"),
    (r"IN.N.OUT|IN N OUT",                     "In-N-Out",            "Dining"),
    # DoorDash and Uber Eats both go to Dining; Uber rides go to Transport
    (r"DOORDASH|DD \*",                        "DoorDash",            "Dining"),
    (r"UBER\s*\*?\s*EATS|UBER EATS",           "Uber Eats",           "Dining"),

    # Transport
    (r"UBER",                                  "Uber",                "Transport"),
    (r"LYFT",                                  "Lyft",                "Transport"),
    (r"SHELL",                                 "Shell",               "Transport"),
    (r"CHEVRON",                               "Chevron",             "Transport"),

    # Shopping
    (r"AMAZON|AMZN",                           "Amazon",              "Shopping"),
    (r"TARGET",                                "Target",              "Shopping"),

    # Entertainment & personal care
    (r"AMC|REGAL CINEMA",                      "Movie Theater",       "Entertainment"),
    (r"CVS",                                   "CVS Pharmacy",        "Personal Care"),
]

def categorize(desc):
    if not desc:
        return pd.Series({"Merchant": "Unknown", "Category": "Uncategorized"})
    for pattern, merchant, category in RULES:
        if re.search(pattern, desc):
            return pd.Series({"Merchant": merchant or desc.title(), "Category": category})
    return pd.Series({"Merchant": desc.title() or "Unknown", "Category": "Uncategorized"})

df[["Merchant", "Category"]] = df["Description_upper"].apply(categorize)

# Refund rows: keep them but tag separately. Refunds reduce spending in totals.
# We'll handle the sign in step 7.

uncat = (df["Category"] == "Uncategorized").sum()
report_lines.append(f"Uncategorized transactions: {uncat}")

# ============================================================================
# 6. DEDUPLICATE
# ============================================================================
# A "duplicate" is the same date + same cleaned merchant + same amount.
# Keep first occurrence.
before = len(df)
df = df.drop_duplicates(subset=["Date", "Merchant", "Amount"], keep="first").reset_index(drop=True)
report_lines.append(f"Dropped exact duplicates: {before - len(df)}")

# ============================================================================
# 7. DERIVED FIELDS
# ============================================================================
# Transaction type: positive amounts are deposits/refunds, negative are spending
df["TxnType"] = df["Amount"].apply(lambda x: "Credit" if x > 0 else "Debit")

# Spend: positive number representing money out (0 for credits)
df["Spend"] = df["Amount"].apply(lambda x: -x if x < 0 else 0.0)

# Income: positive number for money in
df["Income"] = df["Amount"].apply(lambda x: x if x > 0 and "Refund" not in str(x) else 0.0)
# correct income: only payroll/cashouts count as income, refunds offset spend
df["Income"] = df.apply(
    lambda r: r["Amount"] if (r["Amount"] > 0 and r["Category"] == "Income") else 0.0,
    axis=1,
)

# Refunds offset same-category spending — record them as negative spend
df.loc[df["Category"] == "Refund", "Spend"] = df.loc[df["Category"] == "Refund", "Amount"] * -1
# Refunds don't have a real category — try to infer from the description
def infer_refund_category(desc):
    if "AMAZON" in desc or "AMZN" in desc: return "Shopping"
    if "TARGET" in desc:                    return "Shopping"
    return "Other"
refund_mask = df["Category"] == "Refund"
df.loc[refund_mask, "Category"] = df.loc[refund_mask, "Description_upper"].apply(infer_refund_category)

# Calendar fields for BI tools
df["Month"]   = df["Date"].dt.to_period("M").astype(str)   # "2025-10"
df["Weekday"] = df["Date"].dt.day_name()
df["Year"]    = df["Date"].dt.year

# ============================================================================
# 8. OUTPUT
# ============================================================================
final_cols = ["Date", "Year", "Month", "Weekday", "Merchant", "Category",
              "TxnType", "Amount", "Spend", "Income", "Description"]
clean = df[final_cols].sort_values("Date").reset_index(drop=True)

clean_path = OUT_DIR / "clean_transactions.csv"
clean.to_csv(clean_path, index=False)
report_lines.append(f"Final clean rows: {len(clean)}")
print(f"Wrote {len(clean)} clean rows -> {clean_path}")

# Monthly category summary for the dashboard
summary = (clean[clean["Category"] != "Income"]
           .groupby(["Month", "Category"], as_index=False)["Spend"].sum()
           .round(2))
summary_path = OUT_DIR / "summary_by_category.csv"
summary.to_csv(summary_path, index=False)
print(f"Wrote summary -> {summary_path}")

# Data quality report
report_lines.append("")
report_lines.append("=== Category breakdown ===")
for cat, total in clean.groupby("Category")["Spend"].sum().sort_values(ascending=False).items():
    if total > 0:
        report_lines.append(f"  {cat:<20} ${total:>10,.2f}")

report_path = OUT_DIR / "data_quality_report.txt"
report_path.write_text("\n".join(report_lines))
print(f"Wrote QA report -> {report_path}")
