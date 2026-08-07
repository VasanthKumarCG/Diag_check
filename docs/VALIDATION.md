# Validation Order

1. Run `scripts\setup_environment.bat`.
2. Update `.env`.
3. Copy one input file to `Data\input\diagnostic_reports`.
4. Keep `POWERBI_REFRESH_ENABLED=0` for the first run.
5. Run `scripts\run_complete_pipeline.bat`.
6. Run `scripts\verify_database.bat`.
7. Test an identical file again and confirm it is skipped as a duplicate.
8. Load five files, then the complete batch.
9. Configure Power BI and enable `POWERBI_REFRESH_ENABLED=1`.
10. Run the one-click pipeline again and confirm the Power BI refresh reaches `Completed`.
