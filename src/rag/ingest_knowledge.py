from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from psycopg.types.json import Jsonb
from .db import connect
from .ollama_client import DeterministicDummyEmbedder, OllamaClient
from .settings import settings
from .text import chunk_text, normalize_text

REQUIRED={"source_type","source_name","content","approval_status"}

def load_jsonl(path: Path) -> list[dict]:
    docs=[]
    for n,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
        if not line.strip(): continue
        item=json.loads(line); missing=REQUIRED-set(item)
        if missing: raise ValueError(f"{path}:{n} missing {sorted(missing)}")
        docs.append(item)
    return docs

def ingest(path: Path, dummy_embeddings: bool=False) -> tuple[int,int]:
    embedder=DeterministicDummyEmbedder() if dummy_embeddings else OllamaClient()
    model="dummy-sha256" if dummy_embeddings else settings.embed_model
    document_count=chunk_count=0
    with connect() as conn:
        with conn.cursor() as cur:
            for item in load_jsonl(path):
                content=normalize_text(item["content"]); digest=hashlib.sha256(content.encode()).hexdigest()
                cur.execute("""
                    INSERT INTO knowledge.document(source_type,source_id,source_name,source_uri,content_sha256,
                      vehicle_model,vin_scope,sw_release,sw_variant,build_date,primary_ecu,related_ecus,dtc_codes,
                      approval_status,approved_by,approved_at,root_cause,corrective_action,fix_release,validation_result,metadata)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,CASE WHEN %s='Approved' THEN CURRENT_TIMESTAMP END,%s,%s,%s,%s,%s)
                    ON CONFLICT(content_sha256) DO UPDATE SET updated_at=CURRENT_TIMESTAMP
                    RETURNING document_id
                """,(item["source_type"],item.get("source_id"),item["source_name"],item.get("source_uri"),digest,
                      item.get("vehicle_model"),item.get("vin_scope"),item.get("sw_release"),item.get("sw_variant"),item.get("build_date"),
                      item.get("primary_ecu"),item.get("related_ecus",[]),item.get("dtc_codes",[]),item["approval_status"],item.get("approved_by"),
                      item["approval_status"],item.get("root_cause"),item.get("corrective_action"),item.get("fix_release"),item.get("validation_result"),Jsonb(item.get("metadata",{}))))
                document_id=cur.fetchone()[0]
                chunks=chunk_text(content); vectors=embedder.embed(chunks,model=model)
                for idx,(text,vector) in enumerate(zip(chunks,vectors)):
                    cur.execute("""
                      INSERT INTO knowledge.chunk(document_id,chunk_index,chunk_text,token_estimate,chunk_metadata,embedding,embedding_model,embedding_dimension)
                      VALUES(%s,%s,%s,%s,%s,%s::vector,%s,%s)
                      ON CONFLICT(document_id,chunk_index) DO UPDATE SET chunk_text=EXCLUDED.chunk_text,
                        token_estimate=EXCLUDED.token_estimate,chunk_metadata=EXCLUDED.chunk_metadata,
                        embedding=EXCLUDED.embedding,embedding_model=EXCLUDED.embedding_model,embedding_dimension=EXCLUDED.embedding_dimension
                    """,(document_id,idx,text,max(1,len(text)//4),Jsonb({"source_id":item.get("source_id")}),vector,model,len(vector)))
                    chunk_count+=1
                document_count+=1
    return document_count,chunk_count

def main():
    p=argparse.ArgumentParser(); p.add_argument("--input",type=Path,default=Path(settings.output_dir.parent.parent)/"knowledge_samples/dummy_knowledge.jsonl"); p.add_argument("--dummy-embeddings",action="store_true")
    a=p.parse_args(); d,c=ingest(a.input,a.dummy_embeddings); print(f"Ingested documents={d} chunks={c}")
if __name__=="__main__": main()
