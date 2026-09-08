param(
 [switch]$SkipDatabase,
 [switch]$SkipPhase2,
 [switch]$SkipPowerBI,
 [string]$PowerBIFile = ""
)
$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $PSScriptRoot
Set-Location $Root
Write-Host "[1/7] Environment" -ForegroundColor Cyan
& "$PSScriptRoot\setup_environment.bat"; if($LASTEXITCODE){exit $LASTEXITCODE}
Write-Host "[2/7] Tests" -ForegroundColor Cyan
& "$PSScriptRoot\run_tests.bat"; if($LASTEXITCODE){exit $LASTEXITCODE}
Write-Host "[3/7] Phase 1 parse" -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" -m src.pipeline.phase1_parser --input Data\input\diagnostic_reports --output output\phase1; if($LASTEXITCODE){exit $LASTEXITCODE}
if(-not $SkipDatabase){
 Write-Host "[4/7] Database migrations and verification" -ForegroundColor Cyan
 & ".\.venv\Scripts\python.exe" -m src.db.migrate; if($LASTEXITCODE){exit $LASTEXITCODE}
 & ".\.venv\Scripts\python.exe" -m src.pipeline.load_to_postgres --input Data\input\diagnostic_reports; if($LASTEXITCODE){exit $LASTEXITCODE}
 & ".\.venv\Scripts\python.exe" -m src.db.verify; if($LASTEXITCODE){exit $LASTEXITCODE}
}else{Write-Host "[4/7] Database skipped" -ForegroundColor Yellow}
Write-Host "[5/7] Phase 2 knowledge preparation" -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" -m src.rag.build_cases --input knowledge\dummy_cases\txt --output output\knowledge_100.jsonl; if($LASTEXITCODE){exit $LASTEXITCODE}
if(-not $SkipPhase2){
 Write-Host "[6/7] Phase 2 vector ingestion" -ForegroundColor Cyan
 & ".\.venv\Scripts\python.exe" -m src.rag.ingest --input output\knowledge_100.jsonl; if($LASTEXITCODE){exit $LASTEXITCODE}
}else{Write-Host "[6/7] Vector ingestion skipped" -ForegroundColor Yellow}
if(-not $SkipPowerBI -and $PowerBIFile){Write-Host "[7/7] Opening Power BI file for manual refresh" -ForegroundColor Cyan;Start-Process $PowerBIFile}else{Write-Host "[7/7] Power BI open skipped. Refresh the existing PBIX after the database load." -ForegroundColor Yellow}
Write-Host "Complete POC execution finished." -ForegroundColor Green
