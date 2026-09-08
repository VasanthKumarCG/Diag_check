from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path
from psycopg.types.json import Jsonb
import psycopg
from src.db.migrate import kw
from src.rag.ollama import Client
from src.rag import settings
def chunks(t,n=1400):return [t[i:i+n] for i in range(0,len(t),n)]
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);a=p.parse_args();items=[json.loads(x) for x in a.input.read_text(encoding='utf-8').splitlines() if x.strip()];client=Client()
 with psycopg.connect(**kw()) as c:
  with c.cursor() as q:
   for x in items:
    text=x['canonical_content'];h=hashlib.sha256((x.get('source_content') or text).encode()).hexdigest();q.execute("INSERT INTO knowledge.document(source_type,source_id,source_name,source_uri,content_sha256,source_language,canonical_language,source_content,canonical_content,sw_release,primary_ecu,related_ecus,dtc_codes,approval_status,root_cause,corrective_action,validation_result,metadata) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(content_sha256) DO UPDATE SET canonical_content=EXCLUDED.canonical_content,metadata=EXCLUDED.metadata RETURNING document_id",(x['source_type'],x['source_id'],x['source_name'],x['source_uri'],h,x['source_language'],x['canonical_language'],x.get('source_content'),text,x.get('sw_release'),x.get('primary_ecu'),x.get('related_ecus',[]),x.get('dtc_codes',[]),x.get('approval_status','Draft'),x.get('root_cause'),x.get('corrective_action'),x.get('validation_result'),Jsonb(x.get('metadata',{}))));doc=q.fetchone()[0];parts=chunks(text);vecs=client.embed(parts)
    for i,(part,v) in enumerate(zip(parts,vecs)):q.execute('INSERT INTO knowledge.chunk(document_id,chunk_index,chunk_text,embedding,embedding_model) VALUES(%s,%s,%s,%s::vector,%s) ON CONFLICT(document_id,chunk_index) DO UPDATE SET chunk_text=EXCLUDED.chunk_text,embedding=EXCLUDED.embedding,embedding_model=EXCLUDED.embedding_model',(doc,i,part,v,settings.EMBED))
 print('Ingested',len(items),'documents')
if __name__=='__main__':main()
