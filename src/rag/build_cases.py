from __future__ import annotations
import argparse,json
from pathlib import Path
from src.pipeline.phase1_parser import parse
S={'Critical':4,'High':3,'Medium':2,'Low':1};T={'Active':4,'Pending':3,'Intermittent':2,'Stored':1}
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
 for f in sorted(a.input.rglob('*.txt')):
  d=parse(f);top=sorted(d['dtcs'],key=lambda x:(S.get(x.get('severity'),0),T.get(x.get('status'),0),x.get('occurrence_counter') or 0),reverse=True)[:10];language=top[0].get('source_language','en') if top else 'en';content=f"Report {f.name}; release {d['report'].get('sw_i_step')}; "+'; '.join(f"{x['ecu_name']} {x['dtc_code']} {x['description']} {x.get('status')} {x.get('severity')} cause candidate {x.get('possible_cause')}" for x in top)
  rows.append({'source_type':'RCA','source_id':f.stem,'source_name':'Synthetic case '+f.stem,'source_uri':'dummy://'+f.name,'source_language':language,'canonical_language':'en','source_content':' '.join(x.get('source_possible_cause','') for x in top),'canonical_content':content,'content':content,'sw_release':d['report'].get('sw_i_step'),'primary_ecu':top[0]['ecu_name'] if top else None,'related_ecus':sorted({x['ecu_name'] for x in top[1:]}),'dtc_codes':[x['dtc_code'] for x in top],'approval_status':'Draft','root_cause':top[0].get('possible_cause') if top else None,'corrective_action':top[0].get('recommended_check') if top else None,'validation_result':'Synthetic; engineering confirmation required.','metadata':{'synthetic':True,'test_summary':d['test_summary'],'source_file':f.name}})
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n',encoding='utf-8');print('Created',len(rows),'knowledge cases')
if __name__=='__main__':main()
