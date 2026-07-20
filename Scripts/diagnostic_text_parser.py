import argparse
import re
from pathlib import Path
from datetime import datetime
import pandas as pd


# ============================================================
# Diagnostic Text Parser - Phase 1
# Purpose:
#   1. Parse diagnostic TXT files
#   2. Extract ECU metadata
#   3. Extract DTC events
#   4. Extract environment data
#   5. Generate CSV and Excel reports
#   6. Generate starter SQL schema
# ============================================================


def safe_int(value):
    """
    Convert value to integer if possible.
    """
    try:
        return int(str(value).strip())
    except Exception:
        return None


def safe_float_or_int(value):
    """
    Convert environment value to int or float if possible.
    Otherwise return original string.
    """
    value = str(value).strip().rstrip(",")

    try:
        if "." in value:
            return float(value)
        return int(value)
    except Exception:
        return value


def normalize_signal_name(signal_name):
    """
    Convert signal name to a safe column-like name.

    Example:
        Battery Voltage -> Battery_Voltage
        GPS Status      -> GPS_Status
    """
    return re.sub(r"[^A-Za-z0-9]+", "_", signal_name).strip("_")


def classify_fault(description):
    """
    Simple rule-based fault classification.

    This is useful for Phase 1 dashboard grouping.
    Later in Phase 2, this can be replaced or enhanced with AI/RAG.
    """
    description = str(description)

    if "Voltage" in description:
        return "Voltage"
    if "Communication" in description:
        return "Communication"
    if "Sensor" in description:
        return "Sensor"
    if "performance" in description.lower():
        return "Performance"

    return "ECU Specific/Other"


def calculate_risk_score(status, occurrence_counter, priority):
    """
    Simple risk scoring logic for Phase 1.

    Higher score means higher investigation priority.

    Logic:
        - Active DTCs get higher weight
        - Higher priority gets higher weight
        - Higher occurrence count increases score
    """

    status_weight = {
        "Active": 3,
        "Intermittent": 2,
        "Stored": 1
    }.get(str(status), 1)

    occurrence_counter = occurrence_counter if occurrence_counter is not None else 0
    priority = priority if priority is not None else 0

    return (status_weight * 100) + (priority * 20) + occurrence_counter


def parse_diagnostic_file(file_path):
    """
    Parse one diagnostic text file.

    Expected input structure example:

        SW I-Step - 24-07-510
        SA's - A X I H W E D R

        ECU - TCU
        Hardware Version - ...
        Bootloader Version - ...
        SW Version - ...
        Coding - ...

        DTCs

        TCU :
        DTC - 0x9026 - Sensor range fault
        Status - Active
        Occurrence Counter - 33
        Aging Counter - 3
        Priority - 3
        Environment Data:
          Timestamp - 2026-05-27 20:32:00
          RSSI - 624
          GPS Status - 204
    """

    file_path = Path(file_path)

    with open(file_path, "r", encoding="utf-8", errors="replace") as file:
        lines = [line.rstrip() for line in file.readlines()]

    report_header = {
        "FileName": file_path.name,
        "FilePath": str(file_path),
        "SW_I_Step": None,
        "SA_Codes": None
    }

    sa_code_lines = []
    ecu_metadata_records = []

    # ------------------------------------------------------------
    # 1. Parse header and ECU metadata before "DTCs"
    # ------------------------------------------------------------

    dtc_start_index = None
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if line == "DTCs":
            dtc_start_index = i
            break

        sw_match = re.match(r"^SW I-Step\s*-\s*(.+)$", line)
        if sw_match:
            report_header["SW_I_Step"] = sw_match.group(1).strip()

        sa_match = re.match(r"^SA's\s*-\s*(.+)$", line)
        if sa_match:
            sa_code_lines.append(sa_match.group(1).strip())

        ecu_match = re.match(r"^ECU\s*-\s*(.+)$", line)
        if ecu_match:
            ecu_name = ecu_match.group(1).strip()

            metadata = {
                "FileName": file_path.name,
                "SW_I_Step": report_header["SW_I_Step"],
                "ECUName": ecu_name,
                "HardwareVersion": None,
                "BootloaderVersion": None,
                "SWVersion": None,
                "Coding": None
            }

            # Look ahead for the next few ECU metadata lines
            lookahead_lines = lines[i + 1:i + 6]

            for meta_line in lookahead_lines:
                meta_line = meta_line.strip()

                hw_match = re.match(r"^Hardware Version\s*-\s*(.+)$", meta_line)
                bl_match = re.match(r"^Bootloader Version\s*-\s*(.+)$", meta_line)
                sw_match = re.match(r"^SW Version\s*-\s*(.+)$", meta_line)
                coding_match = re.match(r"^Coding\s*-\s*(.+)$", meta_line)

                if hw_match:
                    metadata["HardwareVersion"] = hw_match.group(1).strip()
                elif bl_match:
                    metadata["BootloaderVersion"] = bl_match.group(1).strip()
                elif sw_match:
                    metadata["SWVersion"] = sw_match.group(1).strip()
                elif coding_match:
                    metadata["Coding"] = coding_match.group(1).strip()

            ecu_metadata_records.append(metadata)

        i += 1

    report_header["SA_Codes"] = " | ".join(sa_code_lines)

    # ------------------------------------------------------------
    # 2. Parse DTC section
    # ------------------------------------------------------------

    dtc_event_records = []
    environment_signal_records = []

    current_ecu = None
    current_dtc = None
    inside_environment_data = False

    if dtc_start_index is None:
        return report_header, ecu_metadata_records, dtc_event_records, environment_signal_records

    for raw_line in lines[dtc_start_index + 1:]:
        line = raw_line.strip().rstrip(",")

        if not line:
            continue

        # ECU DTC section example:
        # TCU :
        ecu_section_match = re.match(r"^([A-Z0-9_]+)\s*:\s*$", line)

        if ecu_section_match:
            current_ecu = ecu_section_match.group(1).strip()
            current_dtc = None
            inside_environment_data = False
            continue

        # DTC line example:
        # DTC - 0x9026 - Sensor range fault
        dtc_match = re.match(r"^DTC\s*-\s*(0x[0-9A-Fa-f]+)\s*-\s*(.+)$", line)

        if dtc_match:
            dtc_code = dtc_match.group(1).upper()
            description = dtc_match.group(2).strip()

            current_dtc = {
                "FileName": file_path.name,
                "SW_I_Step": report_header["SW_I_Step"],
                "ECUName": current_ecu,
                "DTCCode": dtc_code,
                "Description": description,
                "FaultCategory": classify_fault(description),
                "Status": None,
                "OccurrenceCounter": None,
                "AgingCounter": None,
                "Priority": None,
                "EventTimestamp": None,
                "RiskScore": None
            }

            dtc_event_records.append(current_dtc)
            inside_environment_data = False
            continue

        if current_dtc is None:
            continue

        # DTC attribute lines
        attribute_match = re.match(
            r"^(Status|Occurrence Counter|Aging Counter|Priority)\s*-\s*(.+)$",
            line
        )

        if attribute_match:
            key = attribute_match.group(1).strip()
            value = attribute_match.group(2).strip()

            if key == "Status":
                current_dtc["Status"] = value
            elif key == "Occurrence Counter":
                current_dtc["OccurrenceCounter"] = safe_int(value)
            elif key == "Aging Counter":
                current_dtc["AgingCounter"] = safe_int(value)
            elif key == "Priority":
                current_dtc["Priority"] = safe_int(value)

            current_dtc["RiskScore"] = calculate_risk_score(
                current_dtc["Status"],
                current_dtc["OccurrenceCounter"],
                current_dtc["Priority"]
            )

            continue

        if line.startswith("Environment Data"):
            inside_environment_data = True
            continue

        # Environment data lines
        if inside_environment_data:
            env_match = re.match(r"^(.+?)\s*-\s*(.+)$", line)

            if env_match:
                signal_name = env_match.group(1).strip()
                signal_value = env_match.group(2).strip().rstrip(",")

                if signal_name == "Timestamp":
                    current_dtc["EventTimestamp"] = signal_value
                else:
                    parsed_signal_value = safe_float_or_int(signal_value)

                    environment_signal_records.append({
                        "FileName": file_path.name,
                        "SW_I_Step": report_header["SW_I_Step"],
                        "ECUName": current_ecu,
                        "DTCCode": current_dtc["DTCCode"],
                        "SignalName": signal_name,
                        "SignalValue": parsed_signal_value,
                        "EventTimestamp": current_dtc["EventTimestamp"]
                    })

                    # Also add the environment signal as a wide column
                    signal_column = normalize_signal_name(signal_name)
                    current_dtc[signal_column] = parsed_signal_value

    return report_header, ecu_metadata_records, dtc_event_records, environment_signal_records


def build_data_quality_report(dtc_df):
    """
    Check missing mandatory fields in DTC dataframe.
    """

    mandatory_fields = [
        "SW_I_Step",
        "ECUName",
        "DTCCode",
        "Description",
        "FaultCategory",
        "Status",
        "OccurrenceCounter",
        "AgingCounter",
        "Priority",
        "EventTimestamp"
    ]

    quality_records = []

    total_rows = len(dtc_df)

    for field in mandatory_fields:
        if field in dtc_df.columns:
            missing_count = int(dtc_df[field].isna().sum())
        else:
            missing_count = total_rows

        missing_percent = round((missing_count / total_rows) * 100, 2) if total_rows else 0

        quality_records.append({
            "Field": field,
            "MissingCount": missing_count,
            "MissingPercent": missing_percent
        })

    return pd.DataFrame(quality_records)


def build_summary_tables(report_df, ecu_df, dtc_df, env_df):
    """
    Build summary tables for Excel and Power BI.
    """

    executive_summary = pd.DataFrame([{
        "FilesProcessed": report_df["FileName"].nunique() if not report_df.empty else 0,
        "ECUMetadataRecords": len(ecu_df),
        "ECUsWithDTCs": dtc_df["ECUName"].nunique() if not dtc_df.empty else 0,
        "DTCRecordCount": len(dtc_df),
        "UniqueDTCCount": dtc_df["DTCCode"].nunique() if not dtc_df.empty else 0,
        "EnvironmentSignalRecordCount": len(env_df),
        "EventDateRangeMin": dtc_df["EventTimestamp"].min() if not dtc_df.empty else None,
        "EventDateRangeMax": dtc_df["EventTimestamp"].max() if not dtc_df.empty else None
    }])

    if dtc_df.empty:
        return {
            "executive_summary": executive_summary,
            "ecu_summary": pd.DataFrame(),
            "status_summary": pd.DataFrame(),
            "category_summary": pd.DataFrame(),
            "priority_summary": pd.DataFrame(),
            "top_risk_dtcs": pd.DataFrame(),
            "data_quality": pd.DataFrame()
        }

    ecu_summary = (
        dtc_df
        .groupby("ECUName")
        .agg(
            DTCCount=("DTCCode", "count"),
            UniqueDTCs=("DTCCode", "nunique"),
            ActiveCount=("Status", lambda x: (x == "Active").sum()),
            StoredCount=("Status", lambda x: (x == "Stored").sum()),
            IntermittentCount=("Status", lambda x: (x == "Intermittent").sum()),
            TotalOccurrences=("OccurrenceCounter", "sum"),
            AveragePriority=("Priority", "mean"),
            MaxRiskScore=("RiskScore", "max")
        )
        .reset_index()
        .sort_values(["TotalOccurrences", "MaxRiskScore"], ascending=False)
    )

    status_summary = (
        dtc_df
        .groupby("Status")
        .size()
        .reset_index(name="DTCCount")
        .sort_values("DTCCount", ascending=False)
    )

    category_summary = (
        dtc_df
        .groupby("FaultCategory")
        .agg(
            DTCCount=("DTCCode", "count"),
            TotalOccurrences=("OccurrenceCounter", "sum"),
            ActiveCount=("Status", lambda x: (x == "Active").sum()),
            MaxRiskScore=("RiskScore", "max")
        )
        .reset_index()
        .sort_values("DTCCount", ascending=False)
    )

    priority_summary = (
        dtc_df
        .groupby("Priority")
        .agg(
            DTCCount=("DTCCode", "count"),
            TotalOccurrences=("OccurrenceCounter", "sum")
        )
        .reset_index()
        .sort_values("Priority")
    )

    top_risk_dtcs = (
        dtc_df
        .sort_values(["RiskScore", "OccurrenceCounter"], ascending=False)
        .head(25)
    )

    data_quality = build_data_quality_report(dtc_df)

    return {
        "executive_summary": executive_summary,
        "ecu_summary": ecu_summary,
        "status_summary": status_summary,
        "category_summary": category_summary,
        "priority_summary": priority_summary,
        "top_risk_dtcs": top_risk_dtcs,
        "data_quality": data_quality
    }


def build_correlation_candidates(dtc_df):
    """
    Simple Phase 1 rule-based correlation candidate report.

    Logic:
        If multiple ECUs report the same fault category on the same event date,
        flag it as a possible cross-ECU correlation candidate.

    This is not final RCA.
    This is only a Phase 1 starter report.
    """

    if dtc_df.empty or "EventTimestamp" not in dtc_df.columns:
        return pd.DataFrame()

    temp_df = dtc_df.copy()

    temp_df["EventDate"] = pd.to_datetime(
        temp_df["EventTimestamp"],
        errors="coerce"
    ).dt.date

    correlation_df = (
        temp_df
        .dropna(subset=["EventDate"])
        .groupby(["EventDate", "FaultCategory"])
        .agg(
            ECUCount=("ECUName", "nunique"),
            DTCCount=("DTCCode", "count"),
            ECUs=("ECUName", lambda x: ", ".join(sorted(set(x)))),
            DTCs=("DTCCode", lambda x: ", ".join(sorted(set(x))))
        )
        .reset_index()
    )

    correlation_df = correlation_df[correlation_df["ECUCount"] >= 2]

    return correlation_df.sort_values(
        ["DTCCount", "ECUCount"],
        ascending=False
    )


def generate_sql_schema(output_sql_path):
    """
    Generate starter SQL schema for Phase 1.
    """

    sql = """
-- ============================================================
-- Phase 1 Diagnostic Intelligence Database - Initial Schema
-- ============================================================

CREATE TABLE DiagnosticReport
(
    ReportID INT IDENTITY PRIMARY KEY,
    FileName VARCHAR(255),
    FilePath VARCHAR(1000),
    SW_I_Step VARCHAR(100),
    SA_Codes VARCHAR(500),
    UploadTimestamp DATETIME DEFAULT GETDATE()
);

CREATE TABLE ECUVersion
(
    ECUVersionID INT IDENTITY PRIMARY KEY,
    ReportID INT,
    FileName VARCHAR(255),
    SW_I_Step VARCHAR(100),
    ECUName VARCHAR(100),
    HardwareVersion VARCHAR(100),
    BootloaderVersion VARCHAR(100),
    SWVersion VARCHAR(100),
    Coding VARCHAR(100)
);

CREATE TABLE DTCEvent
(
    EventID BIGINT IDENTITY PRIMARY KEY,
    ReportID INT,
    FileName VARCHAR(255),
    SW_I_Step VARCHAR(100),
    ECUName VARCHAR(100),
    DTCCode VARCHAR(20),
    Description VARCHAR(500),
    FaultCategory VARCHAR(100),
    Status VARCHAR(50),
    OccurrenceCounter INT,
    AgingCounter INT,
    Priority INT,
    EventTimestamp DATETIME,
    RiskScore INT
);

CREATE TABLE EnvironmentSignal
(
    SignalID BIGINT IDENTITY PRIMARY KEY,
    EventID BIGINT NULL,
    ReportID INT,
    FileName VARCHAR(255),
    SW_I_Step VARCHAR(100),
    ECUName VARCHAR(100),
    DTCCode VARCHAR(20),
    SignalName VARCHAR(100),
    SignalValue VARCHAR(100),
    EventTimestamp DATETIME
);

-- Example Phase 1 trend query:
-- DTC count by software release and ECU
SELECT
    SW_I_Step,
    ECUName,
    DTCCode,
    COUNT(*) AS DTCCount,
    SUM(OccurrenceCounter) AS TotalOccurrences
FROM DTCEvent
GROUP BY
    SW_I_Step,
    ECUName,
    DTCCode
ORDER BY
    TotalOccurrences DESC;
"""

    with open(output_sql_path, "w", encoding="utf-8") as file:
        file.write(sql.strip())


def parse_input_path(input_path):
    """
    Accept either:
        1. Single .txt file
        2. Folder containing multiple .txt files
    """

    input_path = Path(input_path)

    if input_path.is_file():
        return [input_path]

    if input_path.is_dir():
        return sorted(input_path.glob("*.txt"))

    raise FileNotFoundError(f"Input path not found: {input_path}")


def run_parser(input_path, output_path):
    """
    Main execution function.
    """

    input_files = parse_input_path(input_path)
    output_path = Path(output_path)

    csv_output_path = output_path / "csv"
    excel_output_path = output_path / "excel"
    sql_output_path = output_path / "sql"

    csv_output_path.mkdir(parents=True, exist_ok=True)
    excel_output_path.mkdir(parents=True, exist_ok=True)
    sql_output_path.mkdir(parents=True, exist_ok=True)

    all_report_headers = []
    all_ecu_metadata = []
    all_dtc_events = []
    all_environment_signals = []

    for file_path in input_files:
        print(f"Parsing file: {file_path}")

        report_header, ecu_metadata, dtc_events, environment_signals = parse_diagnostic_file(file_path)

        all_report_headers.append(report_header)
        all_ecu_metadata.extend(ecu_metadata)
        all_dtc_events.extend(dtc_events)
        all_environment_signals.extend(environment_signals)

    report_df = pd.DataFrame(all_report_headers)
    ecu_df = pd.DataFrame(all_ecu_metadata)
    dtc_df = pd.DataFrame(all_dtc_events)
    env_df = pd.DataFrame(all_environment_signals)

    # Ensure columns exist even if empty
    if not dtc_df.empty:
        if "RiskScore" not in dtc_df.columns:
            dtc_df["RiskScore"] = dtc_df.apply(
                lambda row: calculate_risk_score(
                    row.get("Status"),
                    row.get("OccurrenceCounter"),
                    row.get("Priority")
                ),
                axis=1
            )

    summary_tables = build_summary_tables(report_df, ecu_df, dtc_df, env_df)
    correlation_candidates = build_correlation_candidates(dtc_df)

    # ------------------------------------------------------------
    # Write CSV files
    # ------------------------------------------------------------

    report_df.to_csv(csv_output_path / "parsed_report_header.csv", index=False)
    ecu_df.to_csv(csv_output_path / "parsed_ecu_metadata.csv", index=False)
    dtc_df.to_csv(csv_output_path / "parsed_dtc_events.csv", index=False)
    env_df.to_csv(csv_output_path / "parsed_environment_signals.csv", index=False)

    summary_tables["ecu_summary"].to_csv(csv_output_path / "summary_ecu.csv", index=False)
    summary_tables["status_summary"].to_csv(csv_output_path / "summary_status.csv", index=False)
    summary_tables["category_summary"].to_csv(csv_output_path / "summary_fault_category.csv", index=False)
    summary_tables["priority_summary"].to_csv(csv_output_path / "summary_priority.csv", index=False)
    summary_tables["data_quality"].to_csv(csv_output_path / "data_quality_report.csv", index=False)
    correlation_candidates.to_csv(csv_output_path / "correlation_candidates.csv", index=False)

    # ------------------------------------------------------------
    # Write Excel report
    # ------------------------------------------------------------

    excel_file = excel_output_path / "Phase1_Diagnostic_Parser_Report.xlsx"

    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
        summary_tables["executive_summary"].to_excel(
            writer,
            sheet_name="00_Executive_Summary",
            index=False
        )

        report_df.to_excel(
            writer,
            sheet_name="01_Report_Header",
            index=False
        )

        ecu_df.to_excel(
            writer,
            sheet_name="02_ECU_Metadata",
            index=False
        )

        dtc_df.to_excel(
            writer,
            sheet_name="03_DTC_Events",
            index=False
        )

        env_df.to_excel(
            writer,
            sheet_name="04_Environment_Signals",
            index=False
        )

        summary_tables["ecu_summary"].to_excel(
            writer,
            sheet_name="05_ECU_Summary",
            index=False
        )

        summary_tables["status_summary"].to_excel(
            writer,
            sheet_name="06_Status_Summary",
            index=False
        )

        summary_tables["category_summary"].to_excel(
            writer,
            sheet_name="07_Category_Summary",
            index=False
        )

        summary_tables["priority_summary"].to_excel(
            writer,
            sheet_name="08_Priority_Summary",
            index=False
        )

        summary_tables["top_risk_dtcs"].to_excel(
            writer,
            sheet_name="09_Top_Risk_DTCs",
            index=False
        )

        summary_tables["data_quality"].to_excel(
            writer,
            sheet_name="10_Data_Quality",
            index=False
        )

        correlation_candidates.to_excel(
            writer,
            sheet_name="11_Correlation_Candidates",
            index=False
        )

    # ------------------------------------------------------------
    # Write SQL schema
    # ------------------------------------------------------------

    generate_sql_schema(sql_output_path / "phase1_initial_schema.sql")

    print("\nParsing completed successfully.")
    print(f"Files processed: {len(input_files)}")
    print(f"ECU metadata records: {len(ecu_df)}")
    print(f"DTC records: {len(dtc_df)}")
    print(f"Environment signal records: {len(env_df)}")
    print(f"\nOutput folder: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Phase 1 Diagnostic Text Parser"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Input diagnostic TXT file or folder containing TXT files"
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Output folder path"
    )

    args = parser.parse_args()

    run_parser(args.input, args.output)


if __name__ == "__main__":
    main()