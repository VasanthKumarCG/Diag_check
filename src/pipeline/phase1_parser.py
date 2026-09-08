from __future__ import annotations
import argparse,csv,json,re
from pathlib import Path
HEADER={'VIN':'vin','SW I-Step':'sw_i_step',"SA's":'sa_codes'}
ECU={'Hardware Version':'hardware_version','Bootloader Version':'bootloader_version','SW Version':'sw_version','Coding':'coding','Diagnostic Address':'diagnostic_address','Calibration Version':'calibration_version','Network':'network','Secure Boot':'secure_boot','OTA State':'ota_state'}
DTC={'Status':'status','Occurrence Counter':'occurrence_counter','Aging Counter':'aging_counter','Priority':'priority','Healing Counter':'healing_counter','Debounce Counter':'debounce_counter','Severity':'severity','First Detected':'first_detected','Last Detected':'last_detected','Confirmation State':'confirmation_state','Possible Cause':'possible_cause','Recommended Check':'recommended_check','Source Language':'source_language','Source Possible Cause':'source_possible_cause','Source Recommended Check':'source_recommended_check'}
TEST={'Test Start':'test_start','Test End':'test_end','Test Type':'test_type','Test Environment':'test_environment','Logger ID':'logger_id','ECU Count':'reported_ecu_count','Total DTCs':'reported_total_dtcs','Active DTCs':'reported_active_dtcs','CAN Frames Captured':'can_frames_captured','CAN FD Frames Captured':'can_fd_frames_captured','Ethernet Packets Captured':'ethernet_packets_captured','Data Completeness':'data_completeness','Overall Result':'overall_result','DISCLAIMER':'disclaimer'}
INT=set(['occurrence_counter','aging_counter','priority','healing_counter','debounce_counter','reported_ecu_count','reported_total_dtcs','reported_active_dtcs','can_frames_captured','can_fd_frames_captured','ethernet_packets_captured'])
def cv(v,k):
 v=v.strip()
 if k in INT:
  try:return int(float(v))
  except:return None
 if k=='data_completeness':
  try:return float(v.replace('%','').strip())
  except:return None
 return v
def parse(path:Path):
 report={'file_name':path.name,'file_path':str(path.resolve()),'sa_codes':[]}; ecus=[];dtcs=[];signals=[];test={};mode='header';current_ecu=None;current_dtc=None;env=False
 for row,line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(),1):
  s=line.strip()
  if not s:continue
  if s=='DTCs':mode='dtc';continue
  if s=='ADDITIONAL VEHICLE TEST INFORMATION':mode='test';env=False;current_dtc=None;continue
  if mode=='header' and s.startswith('ECU - '):
   current_ecu=s.split(' - ',1)[1];ecus.append({'file_name':path.name,'ecu_name':current_ecu,'source_row_number':row});continue
  m=re.match(r'^(.+?)\s*-\s*(.*)$',s)
  if mode=='header':
   if m and m.group(1) in HEADER:
    k=HEADER[m.group(1)];report[k].append(m.group(2)) if k=='sa_codes' else report.__setitem__(k,m.group(2))
   elif m and ecus and m.group(1) in ECU:ecus[-1][ECU[m.group(1)]]=m.group(2)
   continue
  if mode=='test':
   if m and m.group(1) in TEST:test[TEST[m.group(1)]]=cv(m.group(2),TEST[m.group(1)])
   continue
  if s.endswith(':') and s!='Environment Data:':current_ecu=s[:-1];env=False;continue
  dm=re.match(r'^DTC\s*-\s*(\S+)\s*-\s*(.+)$',s)
  if dm:
   current_dtc={'file_name':path.name,'ecu_name':current_ecu,'dtc_code':dm.group(1),'description':dm.group(2),'source_row_number':row};dtcs.append(current_dtc);env=False;continue
  if s=='Environment Data:':env=True;continue
  if not m or not current_dtc:continue
  label,raw=m.group(1),m.group(2)
  if env:
   if label=='Timestamp':current_dtc['event_timestamp']=raw
   else:signals.append({'file_name':path.name,'ecu_name':current_ecu,'dtc_code':current_dtc['dtc_code'],'signal_name':label,'signal_value':raw,'event_timestamp':current_dtc.get('event_timestamp'),'source_row_number':row})
  elif label in DTC:current_dtc[DTC[label]]=cv(raw,DTC[label])
 report['sa_codes']=' '.join(report['sa_codes'])
 for x in ecus:x['sw_i_step']=report.get('sw_i_step')
 for x in dtcs:x['sw_i_step']=report.get('sw_i_step')
 for x in signals:
  x['sw_i_step']=report.get('sw_i_step')
  if not x.get('event_timestamp'):
   found=next((d for d in reversed(dtcs) if d['ecu_name']==x['ecu_name'] and d['dtc_code']==x['dtc_code']),None);x['event_timestamp']=found.get('event_timestamp') if found else None
 return {'report':report,'ecus':ecus,'dtcs':dtcs,'signals':signals,'test_summary':test}
def validate(d):
 t=d['test_summary'];issues=[]
 for rule,a,b in [('ECU_COUNT',len(d['ecus']),t.get('reported_ecu_count')),('DTC_COUNT',len(d['dtcs']),t.get('reported_total_dtcs')),('ACTIVE_COUNT',sum(x.get('status')=='Active' for x in d['dtcs']),t.get('reported_active_dtcs'))]:
  if b is not None and a!=b:issues.append({'rule':rule,'actual':a,'reported':b})
 if t.get('data_completeness') is not None and not 0<=t['data_completeness']<=100:issues.append({'rule':'COMPLETENESS_RANGE'})
 return issues
def write_csv(path,rows):
 if not rows:return
 keys=[]
 for r in rows:
  for k in r:
   if k not in keys:keys.append(k)
 with path.open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def run(input_path:Path,output:Path):
 files=[input_path] if input_path.is_file() else sorted(input_path.rglob('*.txt'));output.mkdir(parents=True,exist_ok=True); reports=[];ecus=[];dtcs=[];signals=[];tests=[];summary=[]
 for f in files:
  d=parse(f);issues=validate(d);reports.append(d['report']);ecus+=d['ecus'];dtcs+=d['dtcs'];signals+=d['signals'];tests.append({'file_name':f.name,**d['test_summary']});summary.append({'file':f.name,'ecus':len(d['ecus']),'dtcs':len(d['dtcs']),'signals':len(d['signals']),'issues':len(issues)})
 write_csv(output/'parsed_report_header.csv',reports);write_csv(output/'parsed_ecu_metadata.csv',ecus);write_csv(output/'parsed_dtc_events.csv',dtcs);write_csv(output/'parsed_environment_signals.csv',signals);write_csv(output/'parsed_vehicle_test_summary.csv',tests);write_csv(output/'validation_summary.csv',summary)
 print(json.dumps({'files':len(files),'reports':len(reports),'ecus':len(ecus),'dtcs':len(dtcs),'signals':len(signals),'issues':sum(x['issues'] for x in summary)},indent=2))
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.input,a.output)
if __name__=='__main__':main()
