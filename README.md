# Excel to dbt: A Spreadsheet Migration, With the Bugs It Was Hiding

A business-critical bookings report lived in a spreadsheet: 400+ rows, nested formulas, VLOOKUPs across five sheets, a summary nobody could fully explain. This project migrates it to a tested dbt + Snowflake pipeline, and shows what the spreadsheet was getting wrong the whole time.

The workbook in `legacy/` is a reproducible recreation of a common enterprise pattern, generated from a seeded script. No proprietary code or data.

---

## The bug the spreadsheet was hiding

The workbook converts local-currency bookings to USD with this formula:

```excel
=IFERROR(Raw_Bookings!H2*VLOOKUP(Raw_Bookings!I2,Rates!$A$2:$B$6,2,FALSE),Raw_Bookings!H2)
```

Read the fallback: **when a currency is missing from the rates sheet, `IFERROR` returns the raw local amount.** The Rates sheet has no BRL entry. So every Brazilian booking is reported as though 1 BRL = 1 USD, silently inflating regional totals. No error, no flag, no way to notice by looking at the report.

In the pipeline, that failure mode cannot happen:

```sql
case
    when rate_to_usd is null then 'MISSING_RATE'
    else 'CONVERTED'
end as conversion_status
```

Unconverted rows are kept, flagged, counted in `missing_rate_booking_count` on the regional mart, and covered by an `accepted_values` test. The problem is visible in the output instead of hidden inside it.

---

## What else the migration fixed

| # | In the workbook | In the pipeline |
|---|---|---|
| 1 | Booking dates stored three ways: real dates, `MM/DD/YYYY` strings, ISO strings | Multi-format parse in `stg_bookings`, `not_null` test on the result |
| 2 | Region typed as `East`, `East `, `east`, `EAST` | `initcap(trim(...))`, `unique` test on region in the mart |
| 3 | Rep names mismatched between sheets (`Jon Smith` vs `John Smith`), silently breaking VLOOKUP quota lookups | `stg_rep_master` alias table resolves every name to a stable `rep_id`, tested `not_null` |
| 4 | Three booking IDs duplicated by a double export, double-counted in totals | Deterministic dedupe in `stg_bookings`, `unique` test on `booking_id` |
| 5 | Currency conversion with a silent `IFERROR` fallback | Explicit `MISSING_RATE` status (above) |
| 6 | A single rate per currency, no history | Rates carry `effective_date`; `fct_bookings` selects the latest rate effective on or before each booking date |
| 7 | Five manager adjustments pasted over formulas, traceable only to "see email 3/12" | Adjustment handling separated from calculation logic; source values preserved in `legacy/` |
| 8 | Grand total hardcoded as `=SUM(E4:E7)+5000`, labeled "true-up per Finance - DO NOT REMOVE" | Totals derived from the fact table; no unexplained constants |
| 9 | Same category logic re-derived in nested IFs across the Calc sheet | Defined once in `mart_regional_performance` |

Point 6 is worth a second look: the spreadsheet applies today's rate to a booking from eighteen months ago. `fct_bookings` does a point-in-time join, so historical bookings convert at the rate that was actually in effect.

---

## Architecture

```text
Excel workbook  ->  Python extraction  ->  RAW seeds  ->  STAGING views  ->  ANALYTICS marts
```

- `legacy/` — the source workbook and its deterministic generator
- `scripts/extract_workbook.py` — pulls sheets to CSV without cleaning; the mess reaches dbt intact, on purpose
- `models/staging/` — `stg_bookings`, `stg_rates`, `stg_rep_targets`, `stg_rep_master`
- `models/marts/` — `fct_bookings` (booking grain, conversion status), `mart_regional_performance` (regional totals by deal category)

Cleaning happens in version-controlled SQL, never by editing the workbook. Every correction is reviewable in a diff.

---

## Data quality

Tests run on every build: unique and not-null booking IDs after dedupe, not-null parsed dates, not-null `rep_id` (catches any unmapped alias), not-null currency and rates, `accepted_values` on conversion status, unique region in the mart.

Reconciliation against the workbook lives in `scripts/parity_check.py`, which compares regional totals side by side, reports only evidence-supported explanations, and fails on unexplained differences.

---

## Running it

```bash
source .venv/bin/activate
python scripts/extract_workbook.py     # workbook -> seeds
dbt build                              # seeds, models, tests
python scripts/parity_check.py         # workbook vs pipeline
dbt docs generate                      # model and column documentation
```

Development, CI, and production targets are separated by dbt profile and Snowflake schema. Credentials are read from environment variables and never committed.

---

## Known state

- Bookings without a matching rate are retained and flagged rather than dropped or silently converted.
- The workbook is intentionally messy and is never modified; regenerate it with `python legacy/generate_messy_workbook_corrected.py`.
- GitHub Actions CI is the next phase.

Built with dbt Core, Snowflake, Python, pandas, and openpyxl.
