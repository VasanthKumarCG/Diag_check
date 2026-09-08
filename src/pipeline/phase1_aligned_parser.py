from __future__ import annotations
import argparse,csv,json,re
from pathlib import Path
from datetime import datetime
HEADER={'VIN':'vin','SW I-Step':'sw_i_step',"SA's":'sa_codes'}
ECU_FIELDS={'Hardware Version':'hardware_version','Bootloader Version':'bootloader_version','SW Version':'sw_version','Coding':'coding','Diagnostic Address':'diagnostic_address','Calibration Version':'calibration_version','Network':'network','Secure Boot':'secure_boot','OTA State':'ota_state'}
DTC_FIELDS={'Status':'status','Occurrence Counter':'occurrence_counter','Aging Counter':'aging_counter','Priority':'priority','Healing Counter':'healing_counter','Debounce Counter':'debounce_counter','Severity':'severity','First Detected':'first_detected','Last Detected':'last_detected','Confirmation State':'confirmation_state','Possible Cause':'possible_cause','Recommended Check':'recommended_check','Source Language':'source_language','Source Possible Cause':'source_possible_cause','Source Recommended Check':'source_recommended_check'}
TEST_FIELDS={'Test Start':'test_start','Test End':'test_end','Test Type':'test_type','Test Environment':'test_environment','Logger ID':'logger_id','ECU Count':'reported_ecu_count','Total DTCs':'reported_total_dtcs','Active DTCs':'reported_active_dtcs','CAN Frames Captured':'can_frames_captured','CAN FD Frames Captured':'can_fd_frames_captured','Ethernet Packets Captured':'ethernet_packets_captured','Data Completeness':'data_completeness','Overall Result':'overall_result','DISCLAIMER':'disclaimer'}
INT_FIELDS={'occurrence_counter','aging_counter','priority','healing_counter','debounce_counter','reported_ecu_count','reported_total_dtcs','reported_active_dtcs','can_frames_captured','can_fd_frames_captured','ethernet_packets_captured'}
def value(v,k):
 v=v.strip()
 if k in INT_FIELDS:
  try:return int(float(v.replace('%','').strip()))
  except:return None
 if k=='data_completeness':
  try:return float(v.replace('%','').strip())
  except:return None
 return v

def parse(path:Path):
 report={'file_name':path.name,'file_path':str(path.resolve()),'sa_codes':[]}; ecus=[]; dtcs=[]; signals=[]; test={}; current_ecu=None; current_dtc=None; mode='header'; env=False
 for source_row,line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(),1):
  s=line.strip()
  if not s: continue
  if s=='DTCs': mode='dtc'; continue
  if s=='ADDITIONAL VEHICLE TEST INFORMATION': mode='test'; current_dtc=None; env=False; continue
  if mode=='header' and s.startswith('ECU - '):
   current_ecu=s.split(' - ',1)[1].strip(); ecus.append({'file_name':path.name,'sw_i_step':report.get('sw_i_step'),'ecu_name':current_ecu,'source_row_number':source_row}); continue
  if mode=='header':
   m=re.match(r'^(.+?)\s*-\s*(.*)$',s)
   if m and m.group(1) in HEADER:
    k=HEADER[m.group(1)]; report[k].append(m.group(2)) if k=='sa_codes' else report.__setitem__(k,m.group(2))
   elif m and ecus and m.group(1) in ECU_FIELDS: ecus[-1][ECU_FIELDS[m.group(1)]]=m.group(2)
   continue
  if mode=='test':
   m=re.match(r'^(.+?)\s*-\s*(.*)$',s)
   if m and m.group(1) in TEST_FIELDS: test[TEST_FIELDS[m.group(1)]]=value(m.group(2),TEST_FIELDS[m.group(1)])
   continue
  if mode=='dtc':
   if s.endswith(':') and not s.startswith('Environment Data'): current_ecu=s[:-1].strip(); env=False; continue
   m=re.match(r'^DTC\s*-\s*(\S+)\s*-\s*(.+)$',s)
   if m:
    current_dtc={'file_name':path.name,'sw_i_step':report.get('sw_i_step'),'ecu_name':current_ecu,'dtc_code':m.group(1),'description':m.group(2),'source_row_number':source_row}; dtcs.append(current_dtc); env=False; continue
   if s=='Environment Data:': env=True; continue
   m=re.match(r'^(.+?)\s*-\s*(.*)$',s)
   if not m or not current_dtc: continue
   label,raw=m.group(1).strip(),m.group(2).strip()
   if env:
    if label=='Timestamp': current_dtc['event_timestamp']=raw
    else: signals.append({'file_name':path.name,'sw_i_step':report.get('sw_i_step'),'ecu_name':current_ecu,'dtc_code':current_dtc['dtc_code'],'signal_name':label,'signal_value':raw,'event_timestamp':current_dtc.get('event_timestamp'),'source_row_number':source_row})
   elif label in DTC_FIELDS: current_dtc[DTC_FIELDS[label]]=value(raw,DTC_FIELDS[label])
 report['sa_codes']=' '.join(report['sa_codes'])
 for x in signals:
  if not x.get('event_timestamp'):
   match=next((d for d in reversed(dtcs) if d['ecu_name']==x['ecu_name'] and d['dtc_code']==x['dtc_code']),None); x['event_timestamp']=match.get('event_timestamp') if match else None
 return {'report':report,'ecus':ecus,'dtcs':dtcs,'signals':signals,'test_summary':test}
def validate(data):
 t=data['test_summary']; issues=[]
 checks=[('ECU_COUNT',len(data['ecus']),t.get('reported_ecu_count')),('DTC_COUNT',len(data['dtcs']),t.get('reported_total_dtcs')),('ACTIVE_COUNT',sum(d.get('status')=='Active' for d in data['dtcs']),t.get('reported_active_dtcs'))]
 for code,actual,reported in checks:
  if reported is not None and actual!=reported: issues.append({'rule':code,'actual':actual,'reported':reported})
 if t.get('data_completeness') is not None and not 0<=t['data_completeness']<=100: issues.append({'rule':'COMPLETENESS_RANGE'})
 return issues
def main():
 p=argparse.ArgumentParser(); p.add_argument('--input',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args(); files=[a.input] if a.input.is_file() else sorted(a.input.rglob('*.txt')); a.output.mkdir(parents=True,exist_ok=True); summary=[]
 for f in files:
  d=parse(f); issues=validate(d); (a.output/(f.stem+'.json')).write_text(json.dumps({'data':d,'issues':issues},ensure_ascii=False,indent=2),encoding='utf-8'); summary.append({'file':f.name,'ecus':len(d['ecus']),'dtcs':len(d['dtcs']),'signals':len(d['signals']),'issues':len(issues)})
 with (a.output/'validation_summary.csv').open('w',newline='',encoding='utf-8-sig') as out:
  w=csv.DictWriter(out,fieldnames=summary[0].keys()); w.writeheader(); w.writerows(summary)
 print(json.dumps({'files':len(files),'issues':sum(x['issues'] for x in summary)},indent=2))
if __name__=='__main__': main()
