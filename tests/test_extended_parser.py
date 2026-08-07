from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'pipeline'))
from checkin_file_parser import parse_diagnostic_file


def test_extended_attributes_and_pending(tmp_path):
    source=tmp_path/'sample.txt'
    source.write_text("""VIN - ABC123\nSW I-Step - 26-01-001\nSA's - A B\nDTCs\nECM :\nDTC - 0xAB12 - Sensor fault\nStatus - Pending\nOccurrence Counter - 2\nAging Counter - 1\nPriority - 3\nHealing Counter - 4\nSeverity - High\nConfirmation State - Pending confirmation\nEnvironment Data:\nTimestamp - 2026-01-02 03:04:05\nVoltage - 12.4\n""",encoding='utf-8')
    _,_,dtcs,signals=parse_diagnostic_file(source)
    assert dtcs[0]['Status']=='Pending'
    assert dtcs[0]['HealingCounter']==4
    assert dtcs[0]['Severity']=='High'
    assert dtcs[0]['ConfirmationState']=='Pending confirmation'
    assert signals[0]['SignalName']=='Voltage'
