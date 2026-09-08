from __future__ import annotations
import os
import psycopg
from dotenv import load_dotenv
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

def connection_kwargs() -> dict:
    names = ["PGHOST","PGPORT","PGDATABASE","PGUSER","PGPASSWORD"]
    missing = [x for x in names if not os.getenv(x)]
    if missing:
        raise RuntimeError("Missing PostgreSQL settings: " + ", ".join(missing))
    return {
        "host": os.environ["PGHOST"], "port": int(os.environ["PGPORT"]),
        "dbname": os.environ["PGDATABASE"], "user": os.environ["PGUSER"],
        "password": os.environ["PGPASSWORD"],
        "connect_timeout": int(os.getenv("PGCONNECT_TIMEOUT", "10")),
    }

def connect():
    return psycopg.connect(**connection_kwargs())
