from pathlib import Path
from src.pipeline.phase1_aligned_parser import parse,validate
ROOT=Path(__file__).resolve().parents[1]
def test_all_100_inputs_reconcile():
 files=list((ROOT/'phase1_inputs').rglob('*.txt')); assert len(files)==100
 for f in files:
  d=parse(f); assert not validate(d), f
  assert len(d['ecus'])==d['test_summary']['reported_ecu_count']
  assert len(d['dtcs'])==d['test_summary']['reported_total_dtcs']
  assert sum(x.get('status')=='Active' for x in d['dtcs'])==d['test_summary']['reported_active_dtcs']
def test_multilingual_source_and_canonical_fields():
 f=next((ROOT/'phase1_inputs').rglob('Prod_Diagnostic_Extended_SYN_003.txt')); d=parse(f); assert any(x.get('source_language') for x in d['dtcs']); assert all(x.get('possible_cause') for x in d['dtcs'])
