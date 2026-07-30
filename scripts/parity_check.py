"""Reconcile the legacy workbook against the dbt pipeline.

Compares regional booking totals from the Excel Regional_Summary sheet against
mart_regional_performance in Snowflake. Differences are labeled only when the
reconciliation contains supporting evidence; an unexplained difference is a
real defect, so the script exits non-zero when one appears.

Credentials come from environment variables only:
    SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD,
    SNOWFLAKE_ROLE, SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA

Usage:
    python scripts/parity_check.py
    python scripts/parity_check.py --markdown > parity_report.md
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

WORKBOOK = Path("legacy/regional_bookings_report_FINAL_v7_corrected.xlsx")
MART = "mart_regional_performance"
TOLERANCE = 0.01  # dollars; below this, treat as rounding

MISSING_RATE_EXPLANATION = (
    "potentially affected by bookings without an applicable currency rate"
)


def read_workbook_summary() -> pd.DataFrame:
    """Read the computed Regional_Summary values from the workbook."""
    if not WORKBOOK.exists():
        sys.exit(f"Workbook not found: {WORKBOOK}")

    raw = pd.read_excel(WORKBOOK, sheet_name="Regional_Summary", header=2, data_only=True)
    raw = raw.rename(columns={raw.columns[0]: "region", raw.columns[4]: "excel_total_usd"})
    raw = raw[["region", "excel_total_usd"]].dropna(subset=["region"])
    raw = raw[~raw["region"].astype(str).str.upper().str.contains("GRAND")]
    raw["region"] = raw["region"].astype(str).str.strip().str.title()
    raw["excel_total_usd"] = pd.to_numeric(raw["excel_total_usd"], errors="coerce").fillna(0.0)
    return raw.reset_index(drop=True)


def read_mart() -> pd.DataFrame:
    """Read regional totals from Snowflake."""
    try:
        import snowflake.connector
    except ImportError:
        sys.exit("snowflake-connector-python is required: pip install 'snowflake-connector-python[pandas]'")

    required = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        sys.exit(f"Missing environment variables: {', '.join(missing)}")

    connection = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ.get("SNOWFLAKE_ROLE"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "BOOKINGS_DB"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA", "ANALYTICS"),
    )
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            select
                region,
                total_bookings_usd,
                booking_count,
                missing_rate_booking_count
            from {MART}
            order by region
            """
        )
        frame = cursor.fetch_pandas_all()
    finally:
        connection.close()

    frame.columns = [c.lower() for c in frame.columns]
    frame["region"] = frame["region"].astype(str).str.strip().str.title()
    frame = frame.rename(columns={"total_bookings_usd": "dbt_total_usd"})
    frame["dbt_total_usd"] = pd.to_numeric(frame["dbt_total_usd"], errors="coerce").fillna(0.0)
    return frame


def explain(row: pd.Series) -> str:
    """Describe only evidence supported by the reconciliation data."""
    if abs(row["difference"]) <= TOLERANCE:
        return "match"

    if row.get("missing_rate_booking_count", 0) > 0:
        return MISSING_RATE_EXPLANATION

    return "unexplained difference"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--markdown", action="store_true", help="emit a markdown report")
    args = parser.parse_args()

    excel = read_workbook_summary()
    mart = read_mart()

    merged = excel.merge(mart, on="region", how="outer").fillna(0.0)
    merged["difference"] = merged["dbt_total_usd"] - merged["excel_total_usd"]
    merged["explanation"] = merged.apply(explain, axis=1)

    excel_total = merged["excel_total_usd"].sum()
    dbt_total = merged["dbt_total_usd"].sum()
    unconverted = int(merged["missing_rate_booking_count"].sum())

    if args.markdown:
        print("# Parity report: workbook vs pipeline\n")
        print("| Region | Excel total (USD) | dbt total (USD) | Difference | Evidence / status |")
        print("|---|---:|---:|---:|---|")
        for _, row in merged.iterrows():
            print(
                f"| {row['region']} | {row['excel_total_usd']:,.2f} | {row['dbt_total_usd']:,.2f} "
                f"| {row['difference']:,.2f} | {row['explanation']} |"
            )
        print(f"\n**Workbook grand total:** {excel_total:,.2f} (excludes the +5000 true-up cell)")
        print(f"\n**Pipeline grand total:** {dbt_total:,.2f}")
        print(f"\n**Bookings with no applicable rate (flagged, not silently converted):** {unconverted}")
        print(
            "\nThe workbook reports these unconverted bookings at their raw local value "
            "because of the IFERROR fallback. The pipeline flags them instead."
        )
    else:
        pd.set_option("display.width", 160)
        print(merged[["region", "excel_total_usd", "dbt_total_usd", "difference", "explanation"]].to_string(index=False))
        print(f"\nWorkbook total: {excel_total:,.2f}")
        print(f"Pipeline total: {dbt_total:,.2f}")
        print(f"Bookings flagged MISSING_RATE: {unconverted}")

    unexplained = merged[merged["explanation"] == "unexplained difference"]
    if not unexplained.empty:
        print("\nUnexplained differences found:", file=sys.stderr)
        print(unexplained.to_string(index=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
