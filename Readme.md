Yes. The safest path is to test the downloaded workspace separately from your current repository, validate one file first, reconcile all 100 files against the Excel summary, test Power BI Desktop, then Power BI Service, and only after that merge it into GitHub.

1. Extract the downloaded ZIP

Assuming the ZIP is in Downloads:

$ZipPath = "$env:USERPROFILE\Downloads\AI-usecase-for-Check-in-Readings-verified.zip"
$TestRoot = "$env:USERPROFILE\Desktop\CheckinPipelineTest"

Remove-Item $TestRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $TestRoot | Out-Null

Expand-Archive `
    -Path $ZipPath `
    -DestinationPath $TestRoot `
    -Force


Move into the extracted project:

Set-Location "$TestRoot\AI-usecase-for-Check-in-Readings-verified"


Confirm the location and tree:

Get-Location
tree /A /F


Open the workspace in VS Code:

code .


Do not overwrite your existing project yet.

2. Protect input data and credentials

Before creating a Git commit, update .gitignore so diagnostic input files are not uploaded accidentally.

Open .gitignore:

notepad .gitignore


Ensure it contains:

# Secrets
.env
*.pem
*.key
*.pfx

# Python
.venv/
__pycache__/
*.pyc
.pytest_cache/
.coverage

# Generated outputs
output/
logs/

# Diagnostic input and processed data
Data/input/diagnostic_reports/*
Data/input/processed/*
Data/input/rejected/*
Data/input/failed/*
!Data/input/diagnostic_reports/.gitkeep
!Data/input/processed/.gitkeep
!Data/input/rejected/.gitkeep
!Data/input/failed/.gitkeep

# Local databases and temporary files
*.db
*.sqlite
*.log
*.tmp

# Power BI and Office temporary files
~$*


Verify that the real .env will be ignored later:

git check-ignore .env


If Git has not been initialized yet, run that command after Step 13.

3. Prepare the Python environment

Run the included setup script:

.\scripts\setup_environment.bat


This should:

Create .venv.
Upgrade pip.
Install packages from requirements.txt.
Copy .env.example to .env if .env does not exist.

Verify the interpreter:

.\.venv\Scripts\python.exe --version


Verify dependencies:

.\.venv\Scripts\python.exe -c "import pandas, openpyxl, psycopg, dotenv, requests; print('Dependencies OK')"


Expected:

Dependencies OK

4. Prepare a clean PostgreSQL database

For the first validation, use a new database rather than an existing database containing earlier public-schema tables.

Suggested database name:

diagnostic_intelligence_test

Using pgAdmin
Open pgAdmin.
Connect to the PostgreSQL server.
Right-click Databases.
Select Create → Database.
Enter:
Database: diagnostic_intelligence_test
Owner: postgres

Save.
Using psql

If psql is available:

psql `
    -h localhost `
    -p 5433 `
    -U postgres `
    -d postgres `
    -c "CREATE DATABASE diagnostic_intelligence_test;"


If the database already exists, PostgreSQL will return an error. That is harmless if the existing test database is intentional, but a new empty database is preferable for the first run.

5. Configure .env

Open the local environment file:

notepad .env


Use this structure:

PGHOST=localhost
PGPORT=5433
PGDATABASE=diagnostic_intelligence_test
PGUSER=postgres
PGPASSWORD=your_actual_local_password
PGCONNECT_TIMEOUT=10

INPUT_PATH=Data/input/diagnostic_reports
OUTPUT_PATH=output
PROCESSED_PATH=Data/input/processed
REJECTED_PATH=Data/input/rejected
FAILED_PATH=Data/input/failed
EXPECTED_SIGNALS_PER_DTC=0
LOG_PATH=logs

POWERBI_REFRESH_ENABLED=0
POWERBI_TENANT_ID=replace_with_tenant_id
POWERBI_CLIENT_ID=replace_with_client_id
POWERBI_CLIENT_SECRET=replace_with_client_secret
POWERBI_WORKSPACE_ID=replace_with_workspace_id
POWERBI_DATASET_ID=replace_with_semantic_model_id
POWERBI_POLL_SECONDS=15
POWERBI_TIMEOUT_SECONDS=1800


For the first tests, keep:

POWERBI_REFRESH_ENABLED=0


Do not add quotes around PostgreSQL values unless the password genuinely contains leading or trailing spaces.

6. Run static validation

Compile every Python source file:

.\.venv\Scripts\python.exe -m compileall -q src tests


Run the automated tests:

.\.venv\Scripts\python.exe -m pytest -v


Or, if you want to use only the built-in test runner:

.\.venv\Scripts\python.exe -m unittest discover -s tests -v


The current workspace includes tests covering:

VIN extraction
extended ECU metadata
DTC parsing
environment-signal timestamp assignment
Pending status
healing counter
severity
confirmation state

All tests should pass before database testing.

7. Deploy the database only

Execute:

.\.venv\Scripts\python.exe .\src\db\database_creation.py


Expected first-run output:

[applied] 01_schema.sql
[applied] 02_quality.sql
[applied] 03_promotion.sql
[applied] 04_reporting_views.sql
[applied] 05_reporting_analytics.sql
[applied] 06_extended_diagnostics.sql


Run the command again:

.\.venv\Scripts\python.exe .\src\db\database_creation.py


Expected second-run output:

[skip] 01_schema.sql
[skip] 02_quality.sql
[skip] 03_promotion.sql
[skip] 04_reporting_views.sql
[skip] 05_reporting_analytics.sql
[skip] 06_extended_diagnostics.sql


The deployment history uses checksums. If a previously deployed migration is edited later, deployment should stop. Add a new migration such as 07_new_feature.sql instead of modifying an applied migration.

Verify database objects

In pgAdmin Query Tool:

SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN ('admin', 'stage', 'raw', 'reporting')
ORDER BY schema_name;


Expected schemas:

admin
raw
reporting
stage


Verify tables and views:

SELECT
    table_schema,
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema IN ('admin', 'stage', 'raw', 'reporting')
ORDER BY table_schema, table_name;


Verify migrations:

SELECT
    script_name,
    sha256,
    applied_at
FROM public.schema_deployment_history
ORDER BY script_name;

8. Perform a one-file parser-only test

Do not start with all 100 files.

Clear the test input directories:

Remove-Item ".\Data\input\diagnostic_reports\*" -Force -ErrorAction SilentlyContinue
Remove-Item ".\Data\input\processed\*" -Force -ErrorAction SilentlyContinue
Remove-Item ".\Data\input\rejected\*" -Force -ErrorAction SilentlyContinue
Remove-Item ".\Data\input\failed\*" -Force -ErrorAction SilentlyContinue


Copy one diagnostic file from your original repository:

$OriginalInput = "C:\Users\vakamma\OneDrive - Capgemini\Desktop\Checkin_file_reader\AI-usecase-for-Check-in-Readings\Data\input\diagnostic_reports"

Copy-Item `
    "$OriginalInput\Prod_Diagnostic_Extended_001.txt" `
    ".\Data\input\diagnostic_reports\" `
    -Force


Run parser and export only:

.\scripts\run_parser_only.bat


Verify output:

Get-ChildItem ".\output\csv"
Get-ChildItem ".\output\excel"


Expected detailed CSV files include:

parsed_report_header.csv
parsed_ecu_metadata.csv
parsed_dtc_events.csv
parsed_environment_signals.csv


Expected Excel file:

output\excel\Phase1_Diagnostic_Parser_Report.xlsx


Open the Excel workbook:

Start-Process ".\output\excel\Phase1_Diagnostic_Parser_Report.xlsx"


Check:

VIN and SW I-Step are populated.
ECU names and extended ECU metadata are populated.
DTC codes and descriptions align with the TXT input.
Pending is retained where present.
Environment signals have timestamps.
Extended fields appear in the DTC export.
No input field is shifted into the wrong column.
9. Perform a one-file PostgreSQL test

Copy the test file back if the earlier parser-only run did not move it. Then run:

.\.venv\Scripts\python.exe `
    .\src\pipeline\postgres_batch_loader.py `
    --input .\Data\input\diagnostic_reports


Expected result:

Data/input/diagnostic_reports
    becomes empty

and the source file moves to:

Data/input/processed


If the file is invalid:

Data/input/rejected


If a technical error occurs:

Data/input/failed


Check the log:

Get-Content ".\logs\postgres_batch_loader.log" -Tail 100


Follow it live:

Get-Content ".\logs\postgres_batch_loader.log" -Wait

10. Verify PostgreSQL row counts and lineage

Run the included verification:

.\scripts\verify_database.bat


Then run these SQL checks.

File inventory
SELECT
    file_id,
    file_name,
    sw_i_step,
    LEFT(file_hash, 12) AS hash_prefix,
    process_status,
    processing_start_time,
    processing_end_time,
    error_message
FROM admin.file_inventory
ORDER BY file_id DESC;

Process execution
SELECT
    process_run_id,
    file_id,
    process_name,
    start_time,
    end_time,
    report_records_loaded,
    ecu_records_loaded,
    dtc_records_loaded,
    environment_records_loaded,
    rejected_records,
    process_status,
    error_message
FROM admin.process_execution_log
ORDER BY process_run_id DESC;

Data-quality issues
SELECT
    rule_code,
    severity,
    field_name,
    invalid_value,
    issue_description,
    COUNT(*) AS issue_count
FROM admin.data_quality_issue
GROUP BY
    rule_code,
    severity,
    field_name,
    invalid_value,
    issue_description
ORDER BY severity, rule_code;

Raw counts
SELECT
    (SELECT COUNT(*) FROM raw.diagnostic_report) AS reports,
    (SELECT COUNT(*) FROM raw.ecu_version) AS ecus,
    (SELECT COUNT(*) FROM raw.dtc_event) AS dtcs,
    (SELECT COUNT(*) FROM raw.environment_signal) AS signals;

Extended-field coverage
SELECT
    COUNT(*) AS total_dtcs,
    COUNT(*) FILTER (WHERE severity IS NOT NULL) AS with_severity,
    COUNT(*) FILTER (WHERE confirmation_state IS NOT NULL) AS with_confirmation,
    COUNT(*) FILTER (WHERE healing_counter IS NOT NULL) AS with_healing_counter,
    COUNT(*) FILTER (WHERE possible_cause IS NOT NULL) AS with_possible_cause,
    COUNT(*) FILTER (
        WHERE extended_attributes <> '{}'::jsonb
    ) AS with_extended_attributes
FROM raw.dtc_event;

Status distribution
SELECT
    status,
    COUNT(*) AS dtc_count
FROM raw.dtc_event
GROUP BY status
ORDER BY dtc_count DESC;


Ensure Pending records, if present in the input, load successfully.

11. Test duplicate-file handling

Copy the exact same source file into the input folder again:

Copy-Item `
    "$OriginalInput\Prod_Diagnostic_Extended_001.txt" `
    ".\Data\input\diagnostic_reports\" `
    -Force


Run the loader:

.\.venv\Scripts\python.exe `
    .\src\pipeline\postgres_batch_loader.py `
    --input .\Data\input\diagnostic_reports


Verify that:

the parser is skipped for the completed hash
no new raw report is inserted
no DTC or signal duplication occurs

Check:

SELECT
    file_hash,
    COUNT(*) AS inventory_rows
FROM admin.file_inventory
GROUP BY file_hash
HAVING COUNT(*) > 1;


Expected:

0 rows

12. Run a five-file validation

Reset the test database if you want a clean comparison, or continue after the one-file test.

Copy five input files:

Get-ChildItem "$OriginalInput\*.txt" |
    Sort-Object Name |
    Select-Object -First 5 |
    Copy-Item -Destination ".\Data\input\diagnostic_reports"


Keep Power BI disabled:

POWERBI_REFRESH_ENABLED=0


Run the one-click flow:

.\scripts\run_complete_pipeline.bat


This performs:

Python compilation
    ↓
Automated tests
    ↓
Database migration deployment
    ↓
Parser and exporter
    ↓
Stage loading
    ↓
Quality validation
    ↓
Raw promotion
    ↓
Power BI step, safely skipped while disabled


After completion:

.\scripts\verify_database.bat


Review:

Get-ChildItem ".\Data\input\processed"
Get-ChildItem ".\Data\input\rejected"
Get-ChildItem ".\Data\input\failed"


Do not proceed to all 100 files if any tested file is unexpectedly rejected or failed.

13. Run all 100 files and reconcile against Excel

Copy all inputs:

Copy-Item `
    "$OriginalInput\*.txt" `
    ".\Data\input\diagnostic_reports\" `
    -Force


Run:

.\scripts\run_complete_pipeline.bat


For the dataset represented by the uploaded Excel workbook, the reconciliation targets are:

Reports:               100
ECU metadata records:  2,693
DTC records:           7,304
Environment signals:  59,832


Treat these as cross-verification targets for the matching input set. If the TXT inputs have changed, the row counts can legitimately differ.

Run:

SELECT
    (SELECT COUNT(*) FROM raw.diagnostic_report) AS reports,
    (SELECT COUNT(*) FROM raw.ecu_version) AS ecus,
    (SELECT COUNT(*) FROM raw.dtc_event) AS dtcs,
    (SELECT COUNT(*) FROM raw.environment_signal) AS signals;


Verify DTC detail is not duplicated by the reporting layer:

SELECT
    (SELECT COUNT(*) FROM raw.dtc_event) AS raw_dtc_count,
    (SELECT COUNT(*) FROM reporting.vw_dtc_detail) AS reporting_dtc_count,
    (SELECT COUNT(*) FROM reporting.vw_extended_dtc_detail) AS extended_dtc_count;


All three DTC counts should match.

Review docs/COLUMN_COVERAGE.csv to see how all workbook fields are stored:

Start-Process ".\docs\COLUMN_COVERAGE.csv"

14. Connect Power BI Desktop

Open the existing Power BI report or create a test report.

In Power BI Desktop:

Home
→ Get data
→ PostgreSQL database


Use:

Server: localhost:5433
Database: diagnostic_intelligence_test


Import:

reporting.vw_dtc_detail
reporting.vw_extended_dtc_detail
reporting.vw_environment_signal_detail
reporting.vw_ecu_health
reporting.vw_release_summary
reporting.vw_pipeline_status
reporting.vw_data_quality
reporting.vw_severity_summary
reporting.vw_confirmation_summary


You should normally use either vw_dtc_detail or vw_extended_dtc_detail as the primary DTC fact, not both in the same model.

Recommended relationship
vw_extended_dtc_detail[dtc_event_id]
               1
               ↓
               *
vw_environment_signal_detail[dtc_event_id]


Use the DTC detail view for:

DTC count
unique DTC count
occurrences
ECU
status
priority
risk
severity
confirmation state
release
fault category

Use the environment-signal view for:

voltage
temperature
network information
speed
signal distribution
DTC-specific environmental analysis

Do not create DTC-count measures from the signal view because one DTC can contain multiple signal rows.

Useful initial slicers
sw_i_step
ecu_name
dtc_code
status
severity
confirmation_state
fault_category
priority
risk_band
event_timestamp
file_name


Refresh Power BI Desktop manually first and verify the expected report totals.

15. Configure Power BI Service refresh

Only after Power BI Desktop works:

Publish the report to a Power BI workspace.
Configure the PostgreSQL data source and gateway.
Ensure the gateway machine can connect to the PostgreSQL server.
Configure credentials for the semantic model.
Give the service principal access to the workspace.
Configure permitted Power BI API access in Microsoft Entra ID.

Update .env:

POWERBI_REFRESH_ENABLED=1
POWERBI_TENANT_ID=your_tenant_id
POWERBI_CLIENT_ID=your_client_id
POWERBI_CLIENT_SECRET=your_client_secret
POWERBI_WORKSPACE_ID=your_workspace_id
POWERBI_DATASET_ID=your_semantic_model_id
POWERBI_POLL_SECONDS=15
POWERBI_TIMEOUT_SECONDS=1800


Test Power BI only:

.\.venv\Scripts\python.exe .\src\db\powerbi_refresh.py


Expected sequence:

Power BI refresh accepted.
Power BI refresh status: Unknown
Power BI refresh status: InProgress
Power BI refresh status: Completed


Then test the complete one-click process:

.\scripts\run_complete_pipeline.bat

16. Prepare the project for GitHub

Before creating a commit, inspect carefully:

Get-ChildItem -Force


Search source files for possible secrets:

Get-ChildItem -Recurse -File |
Where-Object {
    $_.FullName -notmatch '\\(\.venv|\.git|output|logs)(\\|$)'
} |
Select-String `
    -Pattern "PGPASSWORD|CLIENT_SECRET|API_KEY|TOKEN|1234" `
    -CaseSensitive:$false


Review every result.

The repository may contain .env.example placeholders, but must not contain:

.env
real PostgreSQL passwords
Power BI client secrets
access tokens
diagnostic input files
generated output files
logs
customer or vehicle-identifying data


Check ignored files after initializing Git:

git status --ignored --short


You should see .env, .venv, input files, output, and logs marked as ignored.

17. Push to a new GitHub repository
Create the repository on GitHub

Create an empty repository, for example:

AI-usecase-for-Check-in-Readings


Do not ask GitHub to initialize it with a README, .gitignore, or license because your local workspace already contains those files.

Initialize locally

From the verified project root:

git init
git branch -M main


Configure Git identity if required:

git config user.name "Vasanth Kumar Kamma"
git config user.email "vasanthkumarkamma1@gmail.com"


Check ignored content:

git status --ignored --short


Stage the repository:

git add .


Review exactly what will be committed:

git status
git diff --cached --stat
git diff --cached --name-only


Pay particular attention to ensure these are not staged:

.env
.venv
Data/input/diagnostic_reports/*.txt
output/*
logs/*


Commit:

git commit -m "Standardize diagnostic ETL and Power BI refresh pipeline"


Add the remote:

git remote add origin "https://github.com/<your-github-user>/AI-usecase-for-Check-in-Readings.git"


Push:

git push -u origin main

18. Merge into an existing GitHub repository

If your repository already exists, do not initialize a second history inside it.

Clone the existing repository separately:

Set-Location "$env:USERPROFILE\Desktop"

git clone `
    "https://github.com/<your-github-user>/AI-usecase-for-Check-in-Readings.git" `
    "AI-usecase-for-Check-in-Readings-git"


Move into it:

Set-Location ".\AI-usecase-for-Check-in-Readings-git"


Create a feature branch:

git checkout -b feature/verified-diagnostic-pipeline


Copy the validated workspace files into this cloned folder. Do not copy:

.env
.venv
Data input files
output
logs


Then:

git status --short
git diff --stat


Run tests again from the clone:

.\scripts\setup_environment.bat
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\python.exe -m pytest -v


Commit:

git add .
git commit -m "Integrate verified PostgreSQL and Power BI pipeline"


Push the feature branch:

git push -u origin feature/verified-diagnostic-pipeline


Open a pull request from:

feature/verified-diagnostic-pipeline


into:

main

Suggested pull-request description
## Summary

- Standardizes the diagnostic parser and CSV/Excel exporter
- Adds PostgreSQL admin, stage, raw, and reporting layers
- Adds SHA-256 duplicate detection
- Adds database-level data-quality validation
- Preserves extended diagnostic attributes through typed columns and JSONB
- Supports Pending DTC status
- Adds Power BI reporting views
- Adds optional Power BI semantic-model refresh
- Adds one-click batch execution
- Adds unit tests and GitHub Actions validation

## Validation

- Python compilation passed
- Parser tests passed
- Extended-input parser tests passed
- One-file PostgreSQL test completed
- Duplicate test completed
- Five-file batch test completed
- Full batch reconciliation:
  - Reports:
  - ECU records:
  - DTC records:
  - Signal records:
- Power BI Desktop refresh completed
- Power BI Service refresh completed

## Security

- No .env committed
- No passwords or client secrets committed
- No diagnostic input files committed
- No generated output or logs committed

19. GitHub Actions check

The included workflow should run automatically when you push or open a pull request.

It validates:

Dependency installation
Python compilation
Unit tests


Check the repository’s Actions tab. Do not merge the pull request until the workflow is green.

The GitHub-hosted workflow will not connect to your local PostgreSQL server or local Power BI gateway. Those integration tests remain local unless you later provide a secured CI database.

20. Final acceptance checklist

Before merging into main, confirm:

 .env is not committed.
 Input diagnostic files are not committed.
 Parser tests pass.
 Extended parser tests pass.
 Database migrations apply successfully.
 Running migrations twice is safe.
 One-file load succeeds.
 Duplicate-file load does not duplicate raw rows.
 Data-quality rejection sends invalid files to rejected.
 Technical failure sends files to failed.
 Accepted files move to processed.
 Raw counts reconcile with reporting views.
 Full-batch counts reconcile with the Excel summary.
 Pending DTC records load successfully.
 Extended values are present in typed columns or extended_attributes.
 Power BI Desktop refreshes.
 Power BI Service refresh reaches Completed.
 GitHub Actions passes.
 Pull request has been reviewed.
Recommended first command sequence
Set-Location "$env:USERPROFILE\Desktop\CheckinPipelineTest\AI-usecase-for-Check-in-Readings-verified"

.\scripts\setup_environment.bat

notepad .env

.\.venv\Scripts\python.exe -m compileall -q src tests

.\.venv\Scripts\python.exe -m pytest -v

.\.venv\Scripts\python.exe .\src\db\database_creation.py

.\scripts\run_complete_pipeline.bat

.\scripts\verify_database.bat

# Automotive Diagnostic Intelligence POC - Unified Phase 1 and Phase 2

This bundle consolidates the Phase 1 diagnostic parser/database/Power BI foundation with the Phase 2 multilingual historical knowledge and pgvector/Ollama foundation.

## Fastest smoke test

```powershell
.\scripts\run_complete_poc.bat -SkipDatabase -SkipPhase2 -SkipPowerBI
```

## Full local run

Configure `.env`, install pgvector and the approved Ollama models, then run:

```powershell
.\scripts\run_complete_poc.bat -SkipPowerBI
```

After completion, open the existing PBIX and refresh it manually. All bundled diagnostic and historical cases are synthetic.
# Diagnostic Intelligence Phase 1-Aligned Multilingual Dataset
# Diagnostic Intelligence Level 2 Extension

This merge-ready extension starts from the completed Level 1 PostgreSQL and Power BI POC and adds:

- pgvector knowledge schema
- approved-source metadata and provenance
- release, ECU relationship and owner reference data
- historical knowledge ingestion
- Ollama embedding and Qwen JSON analysis client
- hybrid filtered vector retrieval
- deterministic cross-ECU correlation candidates
- release-regression view
- retrieval and AI audit tables
- engineer-feedback storage
- dummy knowledge, releases, ECU graph and owners

## Quick start

1. Copy `.env.level2.example` to `.env` and configure local values.
2. Install pgvector on the PostgreSQL server.
3. Pull the selected embedding and chat models in Ollama.
4. Run `scripts\setup_level2.bat`.
5. Replace dummy reference data before UAT.
6. Run `scripts\ingest_dummy_knowledge.bat` for a smoke test.
7. Obtain a valid `report_id` from `raw.diagnostic_report`.
8. Run `scripts\run_correlation.bat REPORT_ID`.
9. Run `scripts\run_diagnostic_copilot.bat REPORT_ID`.

The dummy embedding mode is available only for unit/integration plumbing tests and must not be used to evaluate semantic retrieval quality.


This package mirrors the shared `Prod_Diagnostic_Extended` input format and adds controlled multilingual evidence fields without changing canonical diagnostic labels. It contains 100 synthetic reports and 100 linked historical cases.

Run:

```powershell
.\scripts\run_all_checks.bat
.\scripts\build_knowledge_jsonl.bat
```
