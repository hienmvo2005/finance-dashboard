# Personal Finance Dashboard

End-to-end data analyst portfolio project: take a messy bank/credit-card export, clean and categorize it in Python, then visualize spending trends, category breakdowns, and month-over-month changes.

**What this demonstrates**

- Working with realistic, messy real-world data (mixed date formats, duplicate rows, inconsistent merchant names, blank fields, pending-vs-posted noise)
- Data cleaning and normalization in pandas
- Regex-based merchant and category mapping
- Deduplication and data quality reporting
- Preparing analysis-ready output for downstream BI tools
- Dashboard design (preview built in HTML; the same data loads directly into Tableau or Power BI)

---

## Project structure

```
finance-dashboard/
├── data/
│   └── raw_transactions.csv          ← simulated messy bank export (358 rows)
├── scripts/
│   ├── generate_raw_data.py          ← creates the messy raw CSV
│   └── clean_transactions.py         ← the main cleaning + categorization pipeline
├── output/
│   ├── clean_transactions.csv        ← analysis-ready, BI-tool-friendly (348 rows)
│   ├── summary_by_category.csv       ← monthly category totals
│   └── data_quality_report.txt       ← auditable record of what was dropped and why
├── dashboard/
│   └── dashboard.html                ← preview of the final dashboard
└── README.md
```

---

## The data

Six months of synthetic transactions (Oct 2025 – Mar 2026) modeled on real bank export quirks:

| Issue | Example in raw data |
|---|---|
| Mixed date formats in one file | `2025-11-03`, `03/05/2026`, `10/22/25` |
| Same merchant, many spellings | `STARBUCKS #04521 SAN DIEGO CA` / `SBUX *MOBILE ORDER 8821` / `starbucks coffee` |
| Pending duplicates of posted rows | `PENDING - EFT WITHDRAWAL PROPERTY MG` |
| True duplicate rows | identical date + description + amount |
| Blank descriptions | empty string with valid amount |
| Inconsistent casing and whitespace | `  ACH CREDIT VENMO CASHOUT   ` |
| Refunds as positive amounts | `AMAZON.COM*REFUND RT4421` |

---

## Methodology

The cleaning pipeline (`scripts/clean_transactions.py`) does the following, in order:

1. **Load as strings.** Read everything as text first to avoid pandas guessing wrong on mixed-format columns.
2. **Strip and collapse whitespace** in descriptions; standardize internal multi-spaces.
3. **Drop unrecoverable rows** — fully empty, unparseable amount, unparseable date. Each drop is counted in the QA report.
4. **Parse dates flexibly** — try `%Y-%m-%d`, `%m/%d/%Y`, `%m/%d/%y` in order, fall back to pandas inference.
5. **Filter pending duplicates** — any row whose description starts with `PENDING` is removed (the posted version exists elsewhere).
6. **Categorize with a rule list** — 28 ordered regex rules map merchant patterns to canonical merchant + category. Order matters: more specific patterns (e.g., `UBER EATS` → Dining) come before broader ones (`UBER` → Transport).
7. **Deduplicate** on `(Date, Merchant, Amount)`, keeping the first occurrence.
8. **Handle refunds** — refunds are tagged as negative spend and back-attributed to the originating category (Amazon refund → Shopping).
9. **Add derived columns** for BI: `Month`, `Year`, `Weekday`, `TxnType` (Credit/Debit), `Spend` (positive number, money out), `Income` (positive number, money in).

### Audit trail

```
Initial rows loaded: 358
Dropped rows with unparseable amount: 1
Dropped pending-transaction duplicates: 4
Uncategorized transactions: 6
Dropped exact duplicates: 5
Final clean rows: 348
```

The 6 remaining "Uncategorized" rows are genuinely-blank-description transactions — there's no signal to recover. They're flagged in the report, not silently lumped in elsewhere.

---

## Key findings

Six months of activity at a glance:

| Metric | Value |
|---|---|
| Total spend | $23,860 |
| Total income | $37,807 |
| Net savings rate | 37% of income |
| Avg monthly spend | $3,977 |
| Largest category | Housing ($12,900 — rent) |
| Largest discretionary | Shopping ($3,341 — mostly Amazon) |
| Most-frequent merchant | Starbucks (69 visits, $489) |
| MoM change last month | +15.8% |

**Behavioral patterns the dashboard surfaces:**

- Coffee runs are tiny per-transaction but add up — **Starbucks: 69 separate transactions averaging $7.09**. Easy lever to pull if cutting spend.
- **Amazon** is the single biggest discretionary line ($2,568 across 32 orders) — a likely target for a "30-day no-impulse-buy" experiment.
- Recurring fixed costs (rent, utilities, subscriptions, gym) total ~$2,400/month — anything above that is variable and within control.
- **Weekend spending is meaningfully higher** than weekday spending — the weekday-pattern chart shows the bite.

---

## Reproducing the project

```bash
# 1. Generate the messy raw CSV
python scripts/generate_raw_data.py

# 2. Clean and categorize
python scripts/clean_transactions.py

# 3. Open the dashboard preview
open dashboard/dashboard.html      # macOS
# or just double-click the file
```

Requires Python 3.9+ and pandas.

---

## Connecting to Tableau or Power BI

`output/clean_transactions.csv` is structured to drop directly into either tool. Recommended dashboard pages:

**Page 1 — Overview**
- KPI cards: Total Spend, Avg Monthly, Latest-Month MoM %, Net Savings
- Line chart: monthly Spend vs Income
- Donut: category share (excl. Housing, since rent dwarfs everything)

**Page 2 — Categories**
- Stacked bar: monthly composition by category
- Bar: top 10 merchants by spend
- Heatmap: month × category MoM % change

**Page 3 — Patterns**
- Bar: spend by day of week
- Histogram: transaction-size distribution
- Scatter: transaction count vs. average ticket per merchant

**Suggested filters:** Date range, Category (multi-select), Min transaction size.

---

## What I would do differently in v2

- **Bring in real bank/CC exports** from multiple accounts and reconcile transfers between them so they don't double-count.
- **Use a fuzzy matcher** (rapidfuzz) for merchant normalization instead of hand-tuned regex — would reduce the 28-rule list to a maintained merchant dictionary.
- **Add a budget table** so the dashboard shows actual vs. budgeted by category, not just absolute spend.
- **Forecast next month's spend** with a simple time-series model — trailing 3-month average is a fine baseline, then layer on category-specific seasonality.
- **Move the pipeline to a notebook** (Jupyter) for the analysis narrative, keep the `.py` script as the production-style version. Both are valuable to show.
