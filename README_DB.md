# AI Use Case for Check-in Readings

A modular diagnostic pipeline for parsing automotive check-in text files, exporting CSV/Excel artifacts, loading validated data into PostgreSQL, serving Power BI reporting views, and optionally refreshing a Power BI semantic model.

## One-click flow

```text
TXT input
  -> parser
  -> CSV and Excel export
  -> PostgreSQL admin/stage/raw/reporting
  -> data-quality validation
  -> promotion and reconciliation
  -> Power BI refresh
```

## First-time setup

```bat
scripts\setup_environment.bat
```

Update `.env`, copy diagnostic `.txt` files to `Data\input\diagnostic_reports`, then run:

```bat
scriptsun_complete_pipeline.bat
```

## Manual checks

```bat
scriptsun_parser_only.bat
scriptserify_database.bat
```

See `docs/VALIDATION.md` and `docs/POWERBI_SETUP.md`.

## Active source of truth

- `src/pipeline/checkin_file_parser.py`
- `src/pipeline/csv_and_excel_file_export.py`
- `src/pipeline/postgres_batch_loader.py`
- `src/db/database_creation.py`
- `src/db/powerbi_refresh.py`
- `Database/01_schema.sql` through `Database/05_reporting_analytics.sql`

Legacy public-schema loaders and experimental unified scripts are intentionally excluded.

## Verified unified runner

```bash
python -m src.pipeline.unified_full_refresh --input Data/input/diagnostic_reports --skip-powerbi
```

The cross-verification extension is migration `Database/06_extended_diagnostics.sql`. See `docs/CROSS_VERIFICATION.md` for the workbook-to-database coverage review.
