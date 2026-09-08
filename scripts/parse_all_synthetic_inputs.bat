@echo off
setlocal
cd /d "%~dp0.."
".venv\Scripts\python.exe" -m src.pipeline.phase1_aligned_parser --input phase1_inputs --output output\phase1_validation
exit /b %ERRORLEVEL%
