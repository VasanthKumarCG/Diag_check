"""Unified entry point for database deployment, extended parser load, DQ, promotion and Power BI refresh.

The implementation delegates to the maintained modules instead of duplicating SQL and
loader logic. This prevents the original Postgres_sql.py from drifting from migrations.
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.db.database_creation import deploy_database_migrations
from src.db.powerbi_refresh import main as refresh_dataset
from src.pipeline import postgres_batch_loader


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy, parse, validate, promote and optionally refresh Power BI")
    parser.add_argument("--deploy-only", action="store_true")
    parser.add_argument("--skip-powerbi", action="store_true")
    args, loader_args = parser.parse_known_args()
    if args.deploy_only:
        deploy_database_migrations()
        return 0
    original_argv = sys.argv
    try:
        sys.argv = [original_argv[0], *loader_args]
        code = postgres_batch_loader.main()
    finally:
        sys.argv = original_argv
    if code != 0 or args.skip_powerbi or os.getenv("POWERBI_REFRESH_ENABLED", "0").lower() not in {"1","true","yes","on"}:
        return code
    return refresh_dataset()


if __name__ == "__main__":
    raise SystemExit(main())
