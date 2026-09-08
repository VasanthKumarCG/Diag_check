@echo off
setlocal
cd /d "%~dp0.."
".venv\Scripts\python.exe" -m src.db.migrate
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m src.pipeline.phase1_parser --input Data\input\diagnostic_reports --output output\phase1
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m src.pipeline.load_to_postgres --input Data\input\diagnostic_reports
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m src.db.verify
exit /b %ERRORLEVEL%
