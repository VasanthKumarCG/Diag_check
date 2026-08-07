@echo off
setlocal
cd /d "%~dp0.."
if exist ".venv\Scripts\python.exe" (set "PY=.venv\Scripts\python.exe") else (set "PY=py -3")
%PY% src\pipeline\checkin_file_parser.py --input Data\input\diagnostic_reports --output output
exit /b %ERRORLEVEL%
