from __future__ import annotations
import os,hashlib
from pathlib import Path
import psycopg
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[2];load_dotenv(ROOT/'.env')
def kw():return {'host':os.environ['PGHOST'],'port':int(os.getenv('PGPORT','5432')),'dbname':os.environ['PGDATABASE'],'user':os.environ['PGUSER'],'password':os.environ['PGPASSWORD'],'connect_timeout':int(os.getenv('PGCONNECT_TIMEOUT','10'))}
def main():
 files=sorted((ROOT/'Database').glob('*.sql'))
 with psycopg.connect(**kw()) as c:
  with c.cursor() as q:
   q.execute('CREATE TABLE IF NOT EXISTS public.schema_deployment_history(script_name TEXT PRIMARY KEY,sha256 CHAR(64),applied_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP)')
   for f in files:
    sql=f.read_text(encoding='utf-8');h=hashlib.sha256(sql.encode()).hexdigest();q.execute('SELECT sha256 FROM public.schema_deployment_history WHERE script_name=%s',(f.name,));r=q.fetchone()
    if r:
     if r[0]!=h:raise RuntimeError(f'Applied migration changed: {f.name}')
     print('[skip]',f.name);continue
    q.execute(sql);q.execute('INSERT INTO public.schema_deployment_history(script_name,sha256) VALUES(%s,%s)',(f.name,h));print('[applied]',f.name)
if __name__=='__main__':main()
