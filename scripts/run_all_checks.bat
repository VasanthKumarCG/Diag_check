@echo off
setlocal
cd /d "%~dp0.."
".venv\Scripts\python.exe" -m compileall -q src tests
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 exit /b 1
call scripts\parse_all_synthetic_inputs.bat
exit /b %ERRORLEVEL%
