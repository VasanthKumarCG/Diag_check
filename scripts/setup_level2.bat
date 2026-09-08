@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
".venv\Scripts\python.exe" -m pip install -r requirements-level2.txt
if not exist ".env" copy ".env.level2.example" ".env" >nul
".venv\Scripts\python.exe" -m src.db.apply_level2_migrations
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m src.rag.load_reference_data
exit /b %ERRORLEVEL%
