@echo off
setlocal
cd /d "%~dp0.."
if "%~1"=="" echo Usage: run_diagnostic_copilot.bat REPORT_ID & exit /b 2
".venv\Scripts\python.exe" -m src.rag.copilot --report-id %1
exit /b %ERRORLEVEL%
