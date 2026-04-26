"""
generate_raw_data.py

Simulates a real-world bank/credit-card CSV export with all the messiness
you'd actually encounter: inconsistent merchant names, duplicate rows,
missing values, mixed date formats, weird casing, location codes appended
to descriptions, etc.

Output: data/raw_transactions.csv
"""

import csv
import random
from datetime import date, timedelta

random.seed(42)  # reproducible

# ---------------------------------------------------------------------------
# Merchant pool — same merchant appears in multiple messy variants on purpose
# ---------------------------------------------------------------------------
MERCHANTS = {
    # (variants), category, typical_amount_range
    "starbucks": (
        ["STARBUCKS #04521 SAN DIEGO CA", "STARBUCKS STORE 04521",
         "starbucks coffee  ", "SBUX *MOBILE ORDER 8821"],
        "coffee", (4.25, 9.50),
    ),
    "amazon": (
        ["AMZN MKTPL*A21XK7", "AMAZON.COM*RT4421", "Amazon.com",
         "AMZN Mktp US*8821B", "AMAZON MKTPLACE PMTS"],
        "shopping", (8.99, 142.50),
    ),
    "trader_joes": (
        ["TRADER JOE'S #221", "TRADER JOES #221 LA JOLLA",
         "trader joe's   ", "TJ'S #221"],
        "groceries", (22.40, 88.75),
    ),
    "ralphs": (
        ["RALPHS #0712", "RALPHS GROCERY 0712 SD",
         "Ralphs Grocery"],
        "groceries", (15.20, 110.00),
    ),
    "chipotle": (
        ["CHIPOTLE 2841", "CHIPOTLE MEXICAN GRILL #2841",
         "chipotle online order"],
        "dining", (11.50, 18.95),
    ),
    "shell_gas": (
        ["SHELL OIL 57441221", "SHELL SERVICE STATION",
         "SHELL OIL 5744 DEL MAR"],
        "transport", (32.00, 68.50),
    ),
    "uber": (
        ["UBER   *TRIP HELP.UBER.COM", "UBER TRIP 8821AB",
         "Uber  *Eats", "UBER *EATS 99214"],
        "transport_or_dining", (8.40, 34.20),  # split below
    ),
    "netflix": (
        ["NETFLIX.COM", "Netflix Subscription",
         "NETFLIX  COM 8662", "netflix.com"],
        "subscriptions", (15.49, 15.49),
    ),
    "spotify": (
        ["SPOTIFY USA NEW YORK NY", "Spotify P0921AB",
         "spotify usa"],
        "subscriptions", (10.99, 10.99),
    ),
    "rent": (
        ["ACH PMT - PROPERTY MGMT LLC", "RENT - APT 4B",
         "EFT WITHDRAWAL PROPERTY MG"],
        "rent", (2150.00, 2150.00),
    ),
    "sdge": (
        ["SDGE ONLINE PMT", "SAN DIEGO GAS & ELEC",
         "SDG&E AUTOPAY"],
        "utilities", (88.40, 184.20),
    ),
    "att": (
        ["AT&T*BILL PAYMENT", "ATT MOBILITY 800-331-0500",
         "AT&T MOBILITY"],
        "utilities", (75.00, 95.00),
    ),
    "target": (
        ["TARGET 00018821", "TARGET T-1882 SAN DIEGO",
         "Target.com *order"],
        "shopping", (18.50, 165.00),
    ),
    "cvs": (
        ["CVS/PHARMACY #04421", "CVS PHARMACY 04421",
         "cvs pharm 4421"],
        "personal_care", (5.99, 42.00),
    ),
    "in_n_out": (
        ["IN-N-OUT BURGER 221", "IN N OUT BURGER #221"],
        "dining", (8.50, 22.40),
    ),
    "yoga_studio": (
        ["CORE POWER YOGA SD", "COREPOWER YOGA #88"],
        "fitness", (24.00, 24.00),
    ),
    "lyft": (
        ["LYFT *RIDE WED 3PM", "Lyft   *Ride Sat 11pm"],
        "transport", (9.20, 28.40),
    ),
    "doordash": (
        ["DD DOORDASH BURGERLO", "DOORDASH*PIZZA HUT",
         "DD *DoorDash Sushi"],
        "dining", (18.40, 44.20),
    ),
    "apple": (
        ["APPLE.COM/BILL", "APL*ITUNES.COM/BILL",
         "Apple.com/Bill 866-712"],
        "subscriptions", (2.99, 9.99),
    ),
    "gym": (
        ["24 HOUR FITNESS 4421", "24HR FITNESS USA"],
        "fitness", (39.99, 39.99),
    ),
    "vons": (
        ["VONS 3221", "VONS STORE 3221 DEL MAR"],
        "groceries", (12.00, 78.50),
    ),
    "gas_chevron": (
        ["CHEVRON 0382214 ", "CHEVRON  #038221"],
        "transport", (28.00, 62.00),
    ),
    "movie": (
        ["AMC ONLINE 4421", "REGAL CINEMAS"],
        "entertainment", (14.50, 38.00),
    ),
}

# Income-side
INCOME = [
    ("DIRECT DEPOSIT - ACME CORP PAYROLL", 2840.50),
    ("PAYROLL DEPOSIT ACME CORP", 2840.50),
    ("ACH CREDIT VENMO CASHOUT", None),  # variable
]

# ---------------------------------------------------------------------------
# Generation logic
# ---------------------------------------------------------------------------
START = date(2025, 10, 1)
END = date(2026, 3, 31)

def date_iter():
    d = START
    while d <= END:
        yield d
        d += timedelta(days=1)

def fmt_date(d):
    """Mix of date formats — like real exports that change format mid-file."""
    fmts = ["%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%-m/%-d/%Y"]
    return d.strftime(random.choice(fmts))

def maybe_blank(v, p=0.03):
    return "" if random.random() < p else v

rows = []

# --- Recurring monthly: rent, utilities, subscriptions, gym ---
for d in date_iter():
    # Rent on the 1st
    if d.day == 1:
        variants, _, (lo, hi) = MERCHANTS["rent"]
        rows.append([d, random.choice(variants), -round(random.uniform(lo, hi), 2)])
    # SDGE around the 12th
    if d.day == 12:
        variants, _, (lo, hi) = MERCHANTS["sdge"]
        rows.append([d, random.choice(variants), -round(random.uniform(lo, hi), 2)])
    # AT&T around 18th
    if d.day == 18:
        variants, _, (lo, hi) = MERCHANTS["att"]
        rows.append([d, random.choice(variants), -round(random.uniform(lo, hi), 2)])
    # Subscriptions
    if d.day == 5:
        for key in ["netflix", "spotify"]:
            variants, _, (lo, hi) = MERCHANTS[key]
            rows.append([d, random.choice(variants), -round(random.uniform(lo, hi), 2)])
    if d.day == 8:
        variants, _, (lo, hi) = MERCHANTS["gym"]
        rows.append([d, random.choice(variants), -round(random.uniform(lo, hi), 2)])
    # Apple iCloud-ish charge
    if d.day == 22 and random.random() < 0.9:
        variants, _, (lo, hi) = MERCHANTS["apple"]
        rows.append([d, random.choice(variants), -round(random.uniform(lo, hi), 2)])

# --- Income: bi-weekly Friday-ish ---
d = START
while d <= END:
    if d.weekday() == 4:  # Friday
        if (d - START).days % 14 < 7:
            desc = random.choice([INCOME[0][0], INCOME[1][0]])
            rows.append([d, desc, 2840.50])
    d += timedelta(days=1)

# Occasional venmo cashouts
for _ in range(8):
    d = START + timedelta(days=random.randint(0, (END - START).days))
    rows.append([d, "ACH CREDIT VENMO CASHOUT", round(random.uniform(20, 180), 2)])

# --- Discretionary: random across the period ---
discretionary_keys = [k for k in MERCHANTS if k not in
                      ("rent", "sdge", "att", "netflix", "spotify", "gym", "apple")]

# Higher frequency for staples
freq = {
    "starbucks": 70, "trader_joes": 22, "ralphs": 14, "chipotle": 18,
    "shell_gas": 10, "uber": 24, "amazon": 32, "target": 12, "cvs": 8,
    "in_n_out": 9, "yoga_studio": 14, "lyft": 11, "doordash": 16,
    "vons": 7, "gas_chevron": 6, "movie": 4,
}

for key, count in freq.items():
    variants, _, (lo, hi) = MERCHANTS[key]
    for _ in range(count):
        d = START + timedelta(days=random.randint(0, (END - START).days))
        amt = -round(random.uniform(lo, hi), 2)
        rows.append([d, random.choice(variants), amt])

# --- Inject realistic mess: duplicates, refunds, blank descriptions ---

# Duplicate ~5 random transactions (true duplicates - same date, desc, amount)
for _ in range(5):
    rows.append(list(random.choice(rows)))

# Refunds: a few positive amounts paired loosely with shopping
for _ in range(4):
    d = START + timedelta(days=random.randint(0, (END - START).days))
    rows.append([d, "AMAZON.COM*REFUND RT4421", round(random.uniform(8, 60), 2)])
for _ in range(2):
    d = START + timedelta(days=random.randint(0, (END - START).days))
    rows.append([d, "TARGET REFUND 00018821", round(random.uniform(5, 35), 2)])

# A couple of completely blank descriptions
for _ in range(3):
    d = START + timedelta(days=random.randint(0, (END - START).days))
    rows.append([d, "", -round(random.uniform(3, 25), 2)])

# Some "PENDING" rows that duplicate posted ones
for _ in range(4):
    base = random.choice(rows)
    rows.append([base[0], f"PENDING - {base[1]}", base[2]])

# Random whitespace / casing weirdness on ~10% of rows
for r in rows:
    if isinstance(r[1], str) and r[1] and random.random() < 0.1:
        if random.random() < 0.5:
            r[1] = r[1].lower()
        else:
            r[1] = "  " + r[1] + "   "

# Shuffle so it doesn't look mechanical
random.shuffle(rows)

# ---------------------------------------------------------------------------
# Write CSV with mixed date formats and some rows missing the amount
# ---------------------------------------------------------------------------
out_path = "/home/claude/finance-dashboard/data/raw_transactions.csv"
with open(out_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Date", "Description", "Amount"])
    for r in rows:
        d, desc, amt = r
        w.writerow([
            fmt_date(d),
            maybe_blank(desc, p=0.01),
            maybe_blank(f"{amt:.2f}", p=0.005),
        ])

print(f"Wrote {len(rows)} rows to {out_path}")
