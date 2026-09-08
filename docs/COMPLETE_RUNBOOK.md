# Complete Runbook

1. Copy `.env.example` to `.env` and configure PostgreSQL.
2. Run `scripts\setup_environment.bat`.
3. Run `scripts\run_tests.bat`.
4. For offline parser and knowledge preparation only, run:
   `scripts\run_complete_poc.bat -SkipDatabase -SkipPhase2 -SkipPowerBI`
5. With PostgreSQL but without pgvector/Ollama, run:
   `scripts\run_complete_poc.bat -SkipPhase2 -SkipPowerBI`
6. With PostgreSQL, pgvector and Ollama configured, run:
   `scripts\run_complete_poc.bat -SkipPowerBI`
7. Open the existing PBIX and select Home > Refresh.
8. Reconcile Power BI totals with PostgreSQL reporting views.
9. Never use Draft synthetic knowledge for production recommendations.
