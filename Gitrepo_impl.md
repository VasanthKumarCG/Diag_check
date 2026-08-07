# Contributing

1. Create a feature branch from `main`.
2. Never commit `.env`, diagnostic input data, generated output, logs, or Power BI secrets.
3. Run `python -m compileall -q src tests`.
4. Run `python -m unittest discover -s tests -v`.
5. Test with one copied diagnostic file before running a full batch.
6. Include database migration changes as a new numbered SQL file. Do not edit an already deployed migration.
