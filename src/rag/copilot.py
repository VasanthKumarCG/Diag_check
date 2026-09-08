from __future__ import annotations
import argparse, json, uuid
from pathlib import Path
from psycopg.types.json import Jsonb
from .correlate import correlate_report
from .db import connect
from .ollama_client import OllamaClient
from .retrieve import retrieve
from .settings import settings
from .text import build_search_text

SYSTEM="""You are an automotive diagnostic assistant. Use only supplied current facts and retrieved evidence.
Do not invent DTCs, fixes, sources, confidence percentages or root causes. Label every cause as a candidate.
Return JSON with keys: case_summary, primary_event_candidate, secondary_effects, possible_causes,
similar_cases, recommended_checks, missing_information, conflicting_evidence, engineering_confirmation_required.
Always set engineering_confirmation_required to true."""

def current_case(report_id: int) -> dict:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT report_id,file_id,file_name,vin,sw_i_step,sa_codes FROM raw.diagnostic_report WHERE report_id=%s",(report_id,)); r=cur.fetchone()
            if not r: raise ValueError(f"Unknown report_id {report_id}")
            report=dict(zip([x.name for x in cur.description],r))
            cur.execute("SELECT dtc_event_id,ecu_name,dtc_code,description,fault_category,status,occurrence_counter,aging_counter,priority,event_timestamp,risk_score,severity,confirmation_state FROM raw.dtc_event WHERE report_id=%s ORDER BY event_timestamp",(report_id,)); cols=[x.name for x in cur.description]; events=[dict(zip(cols,x)) for x in cur.fetchall()]
    return {"report":report,"events":events}

def analyze(report_id: int) -> dict:
    case=current_case(report_id); events=case["events"]
    primary=max(events,key=lambda x:x.get("risk_score") or 0) if events else {}
    query_case={"sw_release":case["report"].get("sw_i_step"),"primary_ecu":primary.get("ecu_name"),"related_ecus":sorted({x["ecu_name"] for x in events if x.get("ecu_name")}),"dtc_codes":sorted({x["dtc_code"] for x in events if x.get("dtc_code")}),"observed_symptoms":"; ".join(f"{x.get('ecu_name')} {x.get('dtc_code')} {x.get('description')}" for x in events[:20]),"environment_summary":"Environment remains in normalized signal records."}
    query_text=build_search_text(query_case)
    retrieval_id,similar=retrieve(query_text,query_case["primary_ecu"],query_case["dtc_codes"])
    correlations=correlate_report(report_id,persist=True)
    payload={"current_case":case,"deterministic_correlations":correlations,"retrieved_evidence":similar}
    result=OllamaClient().chat_json([{"role":"system","content":SYSTEM},{"role":"user","content":json.dumps(payload,default=str)}])
    query_id=uuid.UUID(retrieval_id)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO knowledge.ai_analysis(query_id,report_id,dtc_event_id,model_name,prompt_version,case_summary,response_json) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (query_id,report_id,primary.get("dtc_event_id"),settings.chat_model,"v1",result.get("case_summary"),Jsonb(result)))
    settings.output_dir.mkdir(parents=True,exist_ok=True); out=settings.output_dir/f"report_{report_id}_{query_id}.json"; out.write_text(json.dumps(result,indent=2,default=str),encoding="utf-8")
    return {"query_id":str(query_id),"output":str(out),"analysis":result}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--report-id",type=int,required=True); a=p.parse_args(); print(json.dumps(analyze(a.report_id),indent=2,default=str))
if __name__=="__main__": main()
