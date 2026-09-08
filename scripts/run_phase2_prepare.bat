@echo off
setlocal
cd /d "%~dp0.."
".venv\Scripts\python.exe" -m src.rag.build_cases --input knowledge\dummy_cases\txt --output output\knowledge_100.jsonl
exit /b %ERRORLEVEL%
