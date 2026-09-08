# Phase 1-Aligned Multilingual Extension

## What is included

- 100 synthetic diagnostic reports matching the shared input structure.
- 24-27 ECU metadata blocks per report.
- 50-80 DTCs per report with exact Phase 1 fields.
- ECU-specific environment signals.
- ADDITIONAL VEHICLE TEST INFORMATION and reconciliation fields.
- Canonical English root-cause fields and separate multilingual source fields.
- 100 historical case TXT files, 100 JSON files, one JSONL and one CSV manifest.
- Exact-format parser, reconciliation checks and knowledge conversion.
- Database migrations for vehicle test summary and multilingual DTC evidence.

## Safety

Everything is synthetic. Distributions are for test coverage, not current-market prevalence. No generated cause or recommendation is a confirmed engineering conclusion.

## Integration order

1. Merge into the current feature branch.
2. Add migrations 10 and 11 after existing migrations 01-09. If those numbers are already occupied locally, renumber before first deployment.
3. Run `scripts\run_all_checks.bat`.
4. Run the existing Phase 1 parser on a five-file sample and compare the supplied parser results.
5. Update the existing parser/exporter/loader to persist vehicle test summary and source-language fields.
6. Reconcile reported and parsed ECU, DTC and Active counts.
7. Build knowledge JSONL.
8. Ingest Draft synthetic knowledge only into a test database.
9. Evaluate multilingual and cross-language retrieval.
10. Replace synthetic data with approved historical cases for UAT.

## Remaining work

- Update the existing PostgreSQL loader and promotion procedure for the new summary table and source-language fields.
- Add quality rules for test period, completeness, ECU/DTC/Active reconciliation and allowed overall results.
- Add approved glossary or translation service with human review.
- Add source permissions and knowledge approval workflow.
- Evaluate retrieval precision by language.
- Approve ECU relationships, release sequence, risk thresholds and ownership.
- Add deterministic cross-ECU time-window correlation.
- Enable LLM recommendations only after retrieval quality passes.
