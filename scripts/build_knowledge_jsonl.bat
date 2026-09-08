@echo off
setlocal
cd /d "%~dp0.."
".venv\Scripts\python.exe" -m src.knowledge.build_knowledge_from_phase1 --input phase1_inputs --output output\phase1_knowledge_100.jsonl
exit /b %ERRORLEVEL%
