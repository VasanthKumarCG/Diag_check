import hashlib
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
SQL_FILES = [
    "01_schema.sql",
    "02_quality.sql",
    "03_promotion.sql",
    "04_reporting_views.sql",
    "05_reporting_analytics.sql",
    "06_extended_diagnostics.sql",
    "07_fix_quality_function.sql",
]


def connection_kwargs():
    required = ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError("Missing environment variables: " + ", ".join(missing))
    return {
        "host": os.environ["PGHOST"],
        "port": int(os.environ["PGPORT"]),
        "dbname": os.environ["PGDATABASE"],
        "user": os.environ["PGUSER"],
        "password": os.environ["PGPASSWORD"],
        "connect_timeout": int(os.getenv("PGCONNECT_TIMEOUT", "10")),
    }


def deploy_database_migrations():
    with psycopg.connect(**connection_kwargs()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS public.schema_deployment_history (
                    script_name TEXT PRIMARY KEY,
                    sha256 CHAR(64) NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            for name in SQL_FILES:
                path = ROOT / "Database" / name
                if not path.exists():
                    raise FileNotFoundError(path)
                sql_text = path.read_text(encoding="utf-8")
                checksum = hashlib.sha256(sql_text.encode("utf-8")).hexdigest()
                cursor.execute(
                    "SELECT sha256 FROM public.schema_deployment_history WHERE script_name=%s",
                    (name,),
                )
                row = cursor.fetchone()
                if row:
                    if row[0] != checksum:
                        raise RuntimeError(
                            f"Deployed migration {name} was modified. "
                            "Create a new numbered migration instead."
                        )
                    print(f"[skip] {name}")
                    continue
                cursor.execute(sql_text)
                cursor.execute(
                    "INSERT INTO public.schema_deployment_history(script_name, sha256) VALUES(%s,%s)",
                    (name, checksum),
                )
                print(f"[applied] {name}")
    return connection_kwargs()


if __name__ == "__main__":
    deploy_database_migrations()
