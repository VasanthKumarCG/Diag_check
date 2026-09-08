from __future__ import annotations
import argparse, hashlib, json, shutil
from datetime import datetime
from pathlib import Path
import psycopg
from psycopg.types.json import Jsonb
from src.db.migrate import kw
from src.pipeline.phase1_parser import parse, validate

def sha256(path:Path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def ts(v):
 if not v:return None
 try:return datetime.fromisoformat(str(v))
 except:return None
def integer(v):
 try:return int(v)
 except:return None
def numeric(v):
 try:return float(v)
 except:return None
def risk(d):
 status={'Active':3,'Pending':2,'Intermittent':1,'Stored':0}.get(d.get('status'),0)
 return status*100+(integer(d.get('priority')) or 0)*20+(integer(d.get('occurrence_counter')) or 0)
def load_file(path:Path):
 data=parse(path);issues=validate(data);digest=sha256(path)
 with psycopg.connect(**kw()) as conn:
  with conn.cursor() as q:
   q.execute("SELECT file_id,process_status FROM admin.file_inventory WHERE file_hash=%s",(digest,));old=q.fetchone()
   if old and old[1]=='Completed':return 'duplicate'
   q.execute("""INSERT INTO admin.file_inventory(file_name,file_path,file_hash,file_size_bytes,sw_i_step,process_status)
   VALUES(%s,%s,%s,%s,%s,'Processing') ON CONFLICT(file_hash) DO UPDATE SET processing_start_time=CURRENT_TIMESTAMP,processing_end_time=NULL,process_status='Processing',error_message=NULL RETURNING file_id""",
   (path.name,str(path.resolve()),digest,path.stat().st_size,data['report'].get('sw_i_step')));file_id=q.fetchone()[0]
   q.execute("INSERT INTO admin.process_execution_log(file_id,process_name) VALUES(%s,%s) RETURNING process_run_id",(file_id,'Unified Phase1 load: '+path.name));run_id=q.fetchone()[0]
   if issues:
    for x in issues:q.execute("INSERT INTO admin.data_quality_issue(process_run_id,file_id,rule_code,severity,issue_description) VALUES(%s,%s,%s,'Error',%s)",(run_id,file_id,x['rule'],json.dumps(x)))
    q.execute("UPDATE admin.process_execution_log SET end_time=CURRENT_TIMESTAMP,process_status='Rejected',rejected_records=%s,error_message='Parser reconciliation failed' WHERE process_run_id=%s",(len(issues),run_id));q.execute("UPDATE admin.file_inventory SET processing_end_time=CURRENT_TIMESTAMP,process_status='Rejected',error_message='Parser reconciliation failed' WHERE file_id=%s",(file_id,));return 'rejected'
   r=data['report'];q.execute("""INSERT INTO raw.diagnostic_report(file_id,file_name,file_path,vin,sw_i_step,sa_codes) VALUES(%s,%s,%s,%s,%s,%s)
   ON CONFLICT(file_id) DO UPDATE SET file_name=EXCLUDED.file_name,file_path=EXCLUDED.file_path,vin=EXCLUDED.vin,sw_i_step=EXCLUDED.sw_i_step,sa_codes=EXCLUDED.sa_codes RETURNING report_id""",
   (file_id,path.name,str(path.resolve()),r.get('vin'),r.get('sw_i_step'),r.get('sa_codes')));report_id=q.fetchone()[0]
   q.execute("DELETE FROM raw.ecu_version WHERE report_id=%s",(report_id,));q.execute("DELETE FROM raw.dtc_event WHERE report_id=%s",(report_id,));q.execute("DELETE FROM raw.vehicle_test_summary WHERE report_id=%s",(report_id,))
   for e in data['ecus']:
    q.execute("""INSERT INTO raw.ecu_version(report_id,ecu_name,hardware_version,bootloader_version,sw_version,coding,diagnostic_address,calibration_version,network,secure_boot,ota_state)
    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(report_id,e.get('ecu_name'),e.get('hardware_version'),e.get('bootloader_version'),e.get('sw_version'),e.get('coding'),e.get('diagnostic_address'),e.get('calibration_version'),e.get('network'),e.get('secure_boot'),e.get('ota_state')))
   ids={}
   for d in data['dtcs']:
    q.execute("""INSERT INTO raw.dtc_event(report_id,source_row_number,ecu_name,dtc_code,description,status,occurrence_counter,aging_counter,priority,healing_counter,debounce_counter,severity,first_detected,last_detected,confirmation_state,possible_cause,recommended_check,event_timestamp,risk_score,source_language,source_possible_cause,source_recommended_check,extended_attributes)
    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING dtc_event_id""",
    (report_id,d.get('source_row_number'),d.get('ecu_name'),d.get('dtc_code'),d.get('description'),d.get('status'),integer(d.get('occurrence_counter')),integer(d.get('aging_counter')),integer(d.get('priority')),integer(d.get('healing_counter')),integer(d.get('debounce_counter')),d.get('severity'),ts(d.get('first_detected')),ts(d.get('last_detected')),d.get('confirmation_state'),d.get('possible_cause'),d.get('recommended_check'),ts(d.get('event_timestamp')),risk(d),d.get('source_language','en'),d.get('source_possible_cause'),d.get('source_recommended_check'),Jsonb({})))
    ids[(d.get('ecu_name'),d.get('dtc_code'))]=q.fetchone()[0]
   for s in data['signals']:
    did=ids.get((s.get('ecu_name'),s.get('dtc_code')))
    if did:q.execute("INSERT INTO raw.environment_signal(dtc_event_id,source_row_number,signal_name,signal_value,numeric_signal_value,event_timestamp) VALUES(%s,%s,%s,%s,%s,%s)",(did,s.get('source_row_number'),s.get('signal_name'),s.get('signal_value'),numeric(s.get('signal_value')),ts(s.get('event_timestamp'))))
   t=data['test_summary'];q.execute("""INSERT INTO raw.vehicle_test_summary(report_id,test_start,test_end,test_type,test_environment,logger_id,reported_ecu_count,reported_total_dtcs,reported_active_dtcs,can_frames_captured,can_fd_frames_captured,ethernet_packets_captured,data_completeness,overall_result,disclaimer)
   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(report_id,ts(t.get('test_start')),ts(t.get('test_end')),t.get('test_type'),t.get('test_environment'),t.get('logger_id'),integer(t.get('reported_ecu_count')),integer(t.get('reported_total_dtcs')),integer(t.get('reported_active_dtcs')),integer(t.get('can_frames_captured')),integer(t.get('can_fd_frames_captured')),integer(t.get('ethernet_packets_captured')),numeric(t.get('data_completeness')),t.get('overall_result'),t.get('disclaimer')))
   q.execute("UPDATE admin.process_execution_log SET end_time=CURRENT_TIMESTAMP,process_status='Completed',report_records_loaded=1,ecu_records_loaded=%s,dtc_records_loaded=%s,environment_records_loaded=%s WHERE process_run_id=%s",(len(data['ecus']),len(data['dtcs']),len(data['signals']),run_id));q.execute("UPDATE admin.file_inventory SET processing_end_time=CURRENT_TIMESTAMP,process_status='Completed' WHERE file_id=%s",(file_id,))
 return 'completed'
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);a=p.parse_args();files=[a.input] if a.input.is_file() else sorted(a.input.rglob('*.txt'));counts={'completed':0,'rejected':0,'duplicate':0,'failed':0}
 for f in files:
  try:counts[load_file(f)]+=1
  except Exception as e:counts['failed']+=1;print(f'FAILED {f}: {e}')
 print(json.dumps(counts,indent=2));raise SystemExit(2 if counts['failed'] else 1 if counts['rejected'] else 0)
if __name__=='__main__':main()
