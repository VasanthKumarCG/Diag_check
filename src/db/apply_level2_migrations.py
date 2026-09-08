from __future__ import annotations
import hashlib
from pathlib import Path
from src.rag.db import connect
ROOT=Path(__file__).resolve().parents[2]
FILES=["08_vector_knowledge_base.sql","09_diagnostic_reference_and_correlation.sql"]

def main():
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS public.schema_deployment_history(script_name TEXT PRIMARY KEY,sha256 CHAR(64) NOT NULL,applied_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP)")
            for name in FILES:
                path=ROOT/"Database"/name; sql=path.read_text(encoding="utf-8"); digest=hashlib.sha256(sql.encode()).hexdigest()
                cur.execute("SELECT sha256 FROM public.schema_deployment_history WHERE script_name=%s",(name,)); row=cur.fetchone()
                if row:
                    if row[0]!=digest: raise RuntimeError(f"Applied migration changed: {name}. Create a new migration.")
                    print(f"[skip] {name}"); continue
                cur.execute(sql); cur.execute("INSERT INTO public.schema_deployment_history(script_name,sha256) VALUES(%s,%s)",(name,digest)); print(f"[applied] {name}")
    return 0
if __name__=="__main__": raise SystemExit(main())
