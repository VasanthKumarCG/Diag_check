import argparse, re
from pathlib import Path
from csv_and_excel_file_export import csv_and_excel_file_export

def safe_int(value):
    try: return int(str(value).strip())
    except (TypeError,ValueError): return None

def safe_number(value):
    value=str(value).strip().rstrip(",")
    try: return float(value) if "." in value else int(value)
    except ValueError: return value

def normalize(label):
    """Convert arbitrary extended labels into stable PascalCase CSV columns."""
    return "".join(part[:1].upper()+part[1:] for part in re.split(r"[^A-Za-z0-9]+", str(label)) if part)

def classify_fault(description):
    text=str(description).lower()
    for key,label in [("voltage","Voltage"),("communication","Communication"),("sensor","Sensor"),("performance","Performance")]:
        if key in text: return label
    return "ECU Specific/Other"

def calculate_risk_score(status, occurrence, priority):
    return {"Active":3,"Intermittent":2,"Stored":1}.get(str(status),1)*100 + (priority or 0)*20 + (occurrence or 0)

def parse_diagnostic_file(file_path):
    file_path=Path(file_path); lines=file_path.read_text(encoding="utf-8",errors="replace").splitlines()
    header={"VIN":None,"FileName":file_path.name,"FilePath":str(file_path.resolve()),"SW_I_Step":None,"SA_Codes":None}; sa=[]; ecus=[]; start=None
    i=0
    while i<len(lines):
        line=lines[i].strip()
        if line=="DTCs": start=i; break
        for pattern,key in [(r"^VIN\s*-\s*(.+)$","VIN"),(r"^SW I-Step\s*-\s*(.+)$","SW_I_Step")]:
            m=re.match(pattern,line,re.I)
            if m: header[key]=m.group(1).strip()
        m=re.match(r"^SA's\s*-\s*(.+)$",line,re.I)
        if m: sa.append(m.group(1).strip())
        m=re.match(r"^ECU\s*-\s*(.+)$",line,re.I)
        if m:
            meta={"FileName":file_path.name,"SW_I_Step":header["SW_I_Step"],"ECUName":m.group(1).strip(),"HardwareVersion":None,"BootloaderVersion":None,"SWVersion":None,"Coding":None,"DiagnosticAddress":None,"CalibrationVersion":None,"Network":None,"SecureBoot":None,"OTAState":None}
            field_patterns={"HardwareVersion":r"^Hardware Version\s*-\s*(.+)$","BootloaderVersion":r"^Bootloader Version\s*-\s*(.+)$","SWVersion":r"^SW Version\s*-\s*(.+)$","Coding":r"^Coding\s*-\s*(.+)$","DiagnosticAddress":r"^Diagnostic Address\s*-\s*(.+)$","CalibrationVersion":r"^Calibration Version\s*-\s*(.+)$","Network":r"^Network\s*-\s*(.+)$","SecureBoot":r"^Secure Boot\s*-\s*(.+)$","OTAState":r"^OTA State\s*-\s*(.+)$"}
            for nxt in lines[i+1:min(i+15,len(lines))]:
                t=nxt.strip()
                if t=="DTCs" or re.match(r"^ECU\s*-",t,re.I): break
                for key,pat in field_patterns.items():
                    mm=re.match(pat,t,re.I)
                    if mm: meta[key]=mm.group(1).strip()
            ecus.append(meta)
        i+=1
    header["SA_Codes"]=" | ".join(sa); dtcs=[]; signals=[]
    if start is None: return header,ecus,dtcs,signals
    current_ecu=None; current=None; env=False; env_values=[]; env_timestamp=None
    def flush_env():
        nonlocal env_values,env_timestamp
        if current:
            current["EventTimestamp"]=env_timestamp
            for name,val in env_values: signals.append({"FileName":file_path.name,"SW_I_Step":header["SW_I_Step"],"ECUName":current_ecu,"DTCCode":current["DTCCode"],"SignalName":name,"SignalValue":safe_number(val),"EventTimestamp":env_timestamp})
        env_values=[]; env_timestamp=None
    for raw in lines[start+1:]:
        line=raw.strip().rstrip(",")
        if not line: continue
        m=re.match(r"^([A-Z0-9_]+)\s*:\s*$",line)
        if m: flush_env(); current_ecu=m.group(1); current=None; env=False; continue
        m=re.match(r"^DTC\s*-\s*(0x[0-9A-Fa-f]+)\s*-\s*(.+)$",line)
        if m:
            flush_env(); current={"FileName":file_path.name,"SW_I_Step":header["SW_I_Step"],"ECUName":current_ecu,"DTCCode":m.group(1).upper(),"Description":m.group(2).strip(),"FaultCategory":classify_fault(m.group(2)), "NormalizedFaultCategory":classify_fault(m.group(2)),
                     "Status":None, "OccurrenceCounter":None, "AgingCounter":None, "Priority":None,
                     "HealingCounter":None, "DebounceCounter":None, "Severity":None,
                     "FirstDetected":None, "LastDetected":None, "ConfirmationState":None,
                     "PossibleCause":None, "RecommendedCheck":None, "EventTimestamp":None, "RiskScore":None}; dtcs.append(current); env=False; continue
        if current is None: continue
        if line.lower().startswith("environment data"): env=True; continue
        if not env:
            m=re.match(r"^(.+?)\s*-\s*(.+)$",line)
            if m:
                labels={"status":"Status","occurrence counter":"OccurrenceCounter","aging counter":"AgingCounter","priority":"Priority","healing counter":"HealingCounter","debounce counter":"DebounceCounter","severity":"Severity","first detected":"FirstDetected","last detected":"LastDetected","confirmation state":"ConfirmationState","possible cause":"PossibleCause","recommended check":"RecommendedCheck","normalized fault category":"NormalizedFaultCategory"}
                key=labels.get(m.group(1).strip().lower(),normalize(m.group(1).strip())); raw=m.group(2).strip()
                current[key]=safe_int(raw) if key in {"OccurrenceCounter","AgingCounter","Priority","HealingCounter","DebounceCounter"} else safe_number(raw)
                current["RiskScore"]=calculate_risk_score(current.get("Status"),current.get("OccurrenceCounter"),current.get("Priority")); continue
        if env:
            m=re.match(r"^(.+?)\s*-\s*(.+)$",line)
            if m:
                if m.group(1).strip().lower()=="timestamp": env_timestamp=m.group(2).strip()
                else: env_values.append((m.group(1).strip(),m.group(2).strip()))
    flush_env()
    return header,ecus,dtcs,signals

def parse_input_path(path):
    path=Path(path)
    if path.is_file(): return [path]
    if path.is_dir(): return sorted(path.glob("*.txt"))
    raise FileNotFoundError(path)

def run_parser(input_path,output_path):
    files=parse_input_path(input_path)
    if not files: raise FileNotFoundError(f"No TXT files found in {input_path}")
    reports=[]; ecus=[]; dtcs=[]; signals=[]
    for path in files:
        r,e,d,s=parse_diagnostic_file(path); reports.append(r); ecus.extend(e); dtcs.extend(d); signals.extend(s)
    result=csv_and_excel_file_export(reports,ecus,dtcs,signals,Path(output_path))
    print(f"Files processed: {len(files)}\nECU records: {len(ecus)}\nDTC records: {len(dtcs)}\nSignal records: {len(signals)}")
    return result

def main():
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--output",required=True); a=p.parse_args(); run_parser(a.input,a.output)
if __name__=="__main__": main()
