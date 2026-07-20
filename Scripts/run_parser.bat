@echo off
echo Running Diagnostic Parser...

py scripts\diagnostic_text_parser.py --input input\diagnostic_reports --output output

echo.
echo Parser execution completed.
echo Check output\excel and output\csv folders.
pause