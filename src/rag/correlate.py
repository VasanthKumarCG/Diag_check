from __future__ import annotations
import argparse, json
from pathlib import Path
from .db import connect
from .settings import settings
ROOT=Path(__file__).resolve().parents[2]

def load_graph(path: Path|None=None) -> dict:
    return json.loads((path or ROOT/"config/ecu_relationships.json").read_text(encoding="utf-8"))

def correlate_report(report_id: int, window_seconds: int|None=None, persist: bool=True) -> list[dict]:
    graph=load_graph(); window=window_seconds or graph.get("default_window_seconds",settings.event_window_seconds)
    related={(r["source_ecu"],r["target_ecu"]):r for r in graph["relationships"]}
    related.update({(b,a):r for (a,b),r in list(related.items())})
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT dtc_event_id,ecu_name,dtc_code,status,fault_category,event_timestamp,risk_score FROM raw.dtc_event WHERE report_id=%s ORDER BY event_timestamp",(report_id,))
            cols=[x.name for x in cur.description]; events=[dict(zip(cols,r)) for r in cur.fetchall()]
            candidates=[]
            for i,a in enumerate(events):
                for b in events[i+1:]:
                    rel=related.get((a["ecu_name"],b["ecu_name"]))
                    if not rel or not a["event_timestamp"] or not b["event_timestamp"]: continue
                    delta=abs((b["event_timestamp"]-a["event_timestamp"]).total_seconds())
                    if delta>window: continue
                    rules=["RELATED_ECU","WITHIN_TIME_WINDOW"]
                    score=0.45 + 0.35*(1-delta/max(window,1))
                    if a["fault_category"] in {"Voltage","Communication"}: rules.append("PRIMARY_CATEGORY"); score+=0.1
                    if b["fault_category"]=="Communication": rules.append("SECONDARY_COMMUNICATION"); score+=0.1
                    item={"primary":a,"related":b,"time_delta_seconds":delta,"rule_codes":rules,"score":min(score,1.0),"relationship":rel}
                    candidates.append(item)
            if persist:
                cur.execute("INSERT INTO analytics.correlation_run(report_id,event_window_seconds,algorithm_version) VALUES(%s,%s,%s) RETURNING correlation_run_id",(report_id,window,graph["algorithm_version"])); run=cur.fetchone()[0]
                from psycopg.types.json import Jsonb
                for x in candidates:
                    cur.execute("""INSERT INTO analytics.correlation_candidate(correlation_run_id,primary_dtc_event_id,related_dtc_event_id,primary_ecu,related_ecu,time_delta_seconds,rule_codes,evidence,score)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(run,x["primary"]["dtc_event_id"],x["related"]["dtc_event_id"],x["primary"]["ecu_name"],x["related"]["ecu_name"],x["time_delta_seconds"],x["rule_codes"],Jsonb({"relationship":x["relationship"]}),x["score"]))
                cur.execute("UPDATE analytics.correlation_run SET completed_at=CURRENT_TIMESTAMP,status='Completed' WHERE correlation_run_id=%s",(run,))
    return candidates

def main():
    p=argparse.ArgumentParser(); p.add_argument("--report-id",type=int,required=True); p.add_argument("--window-seconds",type=int); p.add_argument("--no-persist",action="store_true"); a=p.parse_args()
    print(json.dumps(correlate_report(a.report_id,a.window_seconds,not a.no_persist),default=str,indent=2))
if __name__=="__main__": main()
