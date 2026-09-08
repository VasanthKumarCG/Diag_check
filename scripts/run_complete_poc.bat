@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_complete_poc.ps1" %*
exit /b %ERRORLEVEL%
