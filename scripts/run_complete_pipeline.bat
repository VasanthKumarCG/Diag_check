@echo off
setlocal EnableExtensions
set "ROOT=%~dp0.."
cd /d "%ROOT%"

if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    echo ERROR: .venv is missing.
    echo Run scripts\setup_environment.bat first.
    exit /b 10
)

if not exist ".env" (
    echo ERROR: .env is missing. Copy .env.example to .env and configure PostgreSQL.
    exit /b 11
)
if not exist "Data\input\diagnostic_reports" (
    echo ERROR: input folder is missing.
    exit /b 3
)

 echo [1/4] Compiling Python files...
"%PY%" -m compileall -q src tests
if errorlevel 1 exit /b 12

 echo [2/4] Running unit tests...
"%PY%" -m unittest discover -s tests -v
if errorlevel 1 exit /b 13

 echo [3/4] Parsing, exporting, validating, and loading PostgreSQL...
"%PY%" src\pipeline\postgres_batch_loader.py --input Data\input\diagnostic_reports
set "LOAD_RC=%ERRORLEVEL%"
if not "%LOAD_RC%"=="0" (
    echo ERROR: data pipeline stopped with exit code %LOAD_RC%.
    exit /b %LOAD_RC%
)

 echo [4/4] Refreshing Power BI semantic model...
"%PY%" src\db\powerbi_refresh.py
if errorlevel 1 exit /b 5

echo.
echo COMPLETE: PostgreSQL load and Power BI refresh succeeded.
exit /b 0
