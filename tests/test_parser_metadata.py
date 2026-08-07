import tempfile,textwrap,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src/pipeline"))
from checkin_file_parser import parse_diagnostic_file
class Tests(unittest.TestCase):
 def test_metadata(self):
  content=textwrap.dedent("""VIN - ABC123
SW I-Step - 24-10-227
SA's - X Y Z
ECU - TCU
Hardware Version - 1.0.1
Diagnostic Address - 0xF07
Calibration Version - CAL-123
Network - 1000BASE-T1
Secure Boot - Verified
OTA State - Current
DTCs
TCU :
DTC - 0x1234 - Sample sensor fault
Status - Active
Occurrence Counter - 3
Aging Counter - 1
Priority - 2
Environment Data:
RSSI - 624
GPS Status - 204
Timestamp - 2026-01-01 00:00:00""")
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"x.txt";p.write_text(content);h,e,dtc,s=parse_diagnostic_file(p);self.assertEqual(h['VIN'],'ABC123');self.assertEqual(len(e),1);self.assertEqual(len(dtc),1);self.assertEqual(len(s),2);self.assertTrue(all(x['EventTimestamp'] for x in s))
if __name__=="__main__":unittest.main()
