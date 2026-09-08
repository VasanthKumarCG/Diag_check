@echo off
setlocal
cd /d "%~dp0.."
call scripts\run_phase2_prepare.bat
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m src.rag.ingest --input output\knowledge_100.jsonl
exit /b %ERRORLEVEL%
