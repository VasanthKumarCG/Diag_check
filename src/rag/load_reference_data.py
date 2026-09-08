from __future__ import annotations
import csv,json
from pathlib import Path
from .db import connect
ROOT=Path(__file__).resolve().parents[2]

def main():
    with connect() as conn:
        with conn.cursor() as cur:
            with (ROOT/"config/release_reference.csv").open(encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    cur.execute("""INSERT INTO reference.software_release(sw_release,release_sequence,release_date,vehicle_model,sw_variant,release_type,baseline_release,notes)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(sw_release) DO UPDATE SET release_sequence=EXCLUDED.release_sequence,release_date=EXCLUDED.release_date,vehicle_model=EXCLUDED.vehicle_model,sw_variant=EXCLUDED.sw_variant,release_type=EXCLUDED.release_type,baseline_release=EXCLUDED.baseline_release,notes=EXCLUDED.notes""",
                    (r["sw_release"],int(r["release_sequence"]),r["release_date"] or None,r["vehicle_model"],r["sw_variant"],r["release_type"],r["baseline_release"].lower()=="true",r["notes"]))
            graph=json.loads((ROOT/"config/ecu_relationships.json").read_text())
            for r in graph["relationships"]:
                cur.execute("""INSERT INTO reference.ecu_relationship(source_ecu,target_ecu,interaction_type,network,criticality,metadata)
                VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(source_ecu,target_ecu,interaction_type,valid_from_release) DO NOTHING""",
                (r["source_ecu"],r["target_ecu"],r["interaction_type"],r.get("network"),r.get("criticality","Medium"),json.dumps({"dummy":True})))
            with (ROOT/"config/ecu_owners.csv").open(encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    cur.execute("""INSERT INTO reference.ecu_owner(ecu_name,department,team_name,owner_name,contact_email,escalation_path,active)
                    VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(ecu_name) DO UPDATE SET department=EXCLUDED.department,team_name=EXCLUDED.team_name,owner_name=EXCLUDED.owner_name,contact_email=EXCLUDED.contact_email,escalation_path=EXCLUDED.escalation_path,active=EXCLUDED.active""",
                    (r["ecu_name"],r["department"],r["team_name"],r["owner_name"],r["contact_email"],r["escalation_path"],r["active"].lower()=="true"))
    print("Loaded dummy release, ECU relationship and ownership reference data. Replace before UAT.")
if __name__=="__main__": main()
