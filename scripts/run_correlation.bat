@echo off
setlocal
cd /d "%~dp0.."
if "%~1"=="" echo Usage: run_correlation.bat REPORT_ID & exit /b 2
".venv\Scripts\python.exe" -m src.rag.correlate --report-id %1
exit /b %ERRORLEVEL%
