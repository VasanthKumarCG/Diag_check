from pathlib import Path
from src.pipeline.phase1_parser import parse,validate
ROOT=Path(__file__).resolve().parents[1]
def test_reference_inputs_reconcile():
 for name in ['Prod_Diagnostic_Extended_001.txt','Prod_Diagnostic_Extended_002.txt']:
  d=parse(ROOT/'Data/input/diagnostic_reports'/name);assert not validate(d);assert d['report']['vin'];assert d['test_summary']['reported_total_dtcs']==len(d['dtcs'])
def test_100_dummy_cases_parse():
 files=list((ROOT/'knowledge/dummy_cases/txt').rglob('*.txt'));assert len(files)==100
 for f in files[:12]:assert not validate(parse(f))
