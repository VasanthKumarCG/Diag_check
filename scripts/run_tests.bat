@echo off
setlocal
cd /d "%~dp0.."
".venv\Scripts\python.exe" -m compileall -q src tests
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pytest -q
exit /b %ERRORLEVEL%
