# Excel Bookings Analytics

A production-style dbt and Snowflake project that converts a messy Excel bookings workbook into tested, documented analytics models.

## Architecture

```text
Excel workbook
    ↓
Python extraction
    ↓
RAW seeds
    ↓
STAGING views
    ↓
ANALYTICS marts
```

## Project layers

- `legacy/` — source workbook and deterministic generator
- `scripts/` — workbook extraction code
- `seeds/` — CSV inputs loaded into Snowflake `RAW`
- `models/staging/` — cleaned and standardized views
- `models/marts/` — business-ready analytics tables
- `tests/` — project-level data-quality tests
- `.github/workflows/` — CI/CD automation

## Key models

- `stg_bookings` — cleaned and deduplicated bookings with stable `rep_id`
- `stg_rates` — standardized currency rates
- `stg_rep_targets` — annual representative quotas
- `stg_rep_master` — alias-to-ID mapping
- `fct_bookings` — booking-level USD conversion and rate status
- `mart_regional_performance` — regional booking performance by deal category

## Data-quality controls

The project includes tests for:

- required fields;
- unique booking IDs after deduplication;
- stable representative IDs;
- accepted conversion statuses;
- unique reporting regions;
- documented models and columns.

## Running locally

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Extract workbook inputs:

```bash
python scripts/extract_workbook.py
```

Load seeds and build the full project:

```bash
dbt build
```

Generate documentation:

```bash
dbt docs generate
```

## Environments and CI/CD

Development, CI, and production targets are separated through dbt profiles and Snowflake schemas. Changes are developed on feature branches, validated through automated checks, and merged through pull requests into protected `main`.

Credentials are never committed to the repository.

## Current limitations

- The source workbook contains intentionally messy values and duplicate booking IDs.
- Bookings without a matching currency rate are retained and flagged as `MISSING_RATE`.
- GitHub Actions CI/CD will be configured in the next project phase.
