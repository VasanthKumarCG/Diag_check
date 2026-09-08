@echo off
setlocal
cd /d "%~dp0.."
".venv\Scripts\python.exe" -m src.rag.ingest_knowledge --input knowledge_samples\dummy_knowledge.jsonl
exit /b %ERRORLEVEL%
