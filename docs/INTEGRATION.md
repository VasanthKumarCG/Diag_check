# Integration with the Existing Repository

Copy this extension into the existing repository root. Do not overwrite `.env`.

- Add `08_vector_knowledge_base.sql` and `09_diagnostic_reference_and_correlation.sql` to the existing migration list after migration 07.
- Copy `src/rag` and `src/db/apply_level2_migrations.py`.
- Copy `config`, `knowledge_samples`, scripts and tests.
- Merge `requirements-level2.txt` into the standard requirements only after the POC is accepted.
- Keep dummy records isolated and replace them before UAT.
- Never commit approved confidential RCA/Jira content unless repository access and data classification permit it.
