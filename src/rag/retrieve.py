from __future__ import annotations
import uuid
from psycopg.types.json import Jsonb
from .db import connect
from .ollama_client import OllamaClient
from .settings import settings

def retrieve(query_text: str, primary_ecu: str|None=None, dtc_codes: list[str]|None=None, top_k: int|None=None) -> tuple[str,list[dict]]:
    query_id=str(uuid.uuid4()); vector=OllamaClient().embed([query_text])[0]; top_k=top_k or settings.top_k
    predicates=["1=1"]; params=[]
    if settings.approved_only: predicates.append("d.approval_status='Approved'")
    if primary_ecu:
        predicates.append("(d.primary_ecu=%s OR %s=ANY(d.related_ecus))"); params.extend([primary_ecu,primary_ecu])
    if dtc_codes:
        predicates.append("d.dtc_codes && %s::text[]"); params.append(dtc_codes)
    sql=f"""
      SELECT c.chunk_id,d.document_id,d.source_type,d.source_id,d.source_name,d.source_uri,d.sw_release,
             d.primary_ecu,d.related_ecus,d.dtc_codes,d.root_cause,d.corrective_action,d.fix_release,
             c.chunk_text,(c.embedding <=> %s::vector) AS distance
      FROM knowledge.chunk c JOIN knowledge.document d ON d.document_id=c.document_id
      WHERE {' AND '.join(predicates)}
      ORDER BY c.embedding <=> %s::vector LIMIT %s
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql,[vector,*params,vector,top_k]); cols=[x.name for x in cur.description]; rows=[dict(zip(cols,r)) for r in cur.fetchall()]
            for rank,row in enumerate(rows,1):
                cur.execute("INSERT INTO knowledge.retrieval_audit(query_id,query_text,query_metadata,chunk_id,rank_number,distance,embedding_model) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                    (query_id,query_text,Jsonb({"primary_ecu":primary_ecu,"dtc_codes":dtc_codes or []}),row["chunk_id"],rank,row["distance"],settings.embed_model))
    return query_id,rows
