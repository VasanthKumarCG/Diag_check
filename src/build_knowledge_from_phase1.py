from __future__ import annotations
import argparse,json
from pathlib import Path
from src.pipeline.phase1_aligned_parser import parse
SEV={'Critical':4,'High':3,'Medium':2,'Low':1}; STAT={'Active':4,'Pending':3,'Intermittent':2,'Stored':1}
def main():
 p=argparse.ArgumentParser(); p.add_argument('--input',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args(); rows=[]
 for f in sorted(a.input.rglob('*.txt')):
  d=parse(f); ranked=sorted(d['dtcs'],key=lambda x:(SEV.get(x.get('severity'),0),STAT.get(x.get('status'),0),x.get('occurrence_counter') or 0),reverse=True)[:10]
  source_lang=ranked[0].get('source_language','en') if ranked else 'en'
  content=f"Report {f.name}; SW I-Step {d['report'].get('sw_i_step')}; "+'; '.join(f"{x['ecu_name']} {x['dtc_code']} {x['description']} status {x.get('status')} severity {x.get('severity')} occurrences {x.get('occurrence_counter')} possible cause {x.get('possible_cause')}" for x in ranked)
  rows.append({'source_type':'RCA','source_id':f.stem,'source_name':f'Synthetic case from {f.name}','source_uri':f'dummy://phase1/{f.name}','source_language':source_lang,'canonical_language':'en','sw_release':d['report'].get('sw_i_step'),'primary_ecu':ranked[0]['ecu_name'] if ranked else None,'related_ecus':sorted({x['ecu_name'] for x in ranked[1:]}),'dtc_codes':[x['dtc_code'] for x in ranked],'approval_status':'Draft','root_cause':ranked[0].get('possible_cause') if ranked else None,'corrective_action':ranked[0].get('recommended_check') if ranked else None,'validation_result':'Synthetic; engineering confirmation required.','source_content':' '.join(x.get('source_possible_cause','') for x in ranked if x.get('source_possible_cause')),'canonical_content':content,'content':content,'metadata':{'synthetic':True,'test_summary':d['test_summary'],'source_file':f.name}})
 a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n',encoding='utf-8'); print(f'Created {len(rows)} knowledge records')
if __name__=='__main__': main()
