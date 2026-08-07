from pathlib import Path
import pandas as pd

REPORT_COLUMNS = ["VIN","FileName","FilePath","SW_I_Step","SA_Codes"]
ECU_COLUMNS = ["FileName","SW_I_Step","ECUName","HardwareVersion","BootloaderVersion","SWVersion","Coding","DiagnosticAddress","CalibrationVersion","Network","SecureBoot","OTAState"]
DTC_COLUMNS = ["FileName","SW_I_Step","ECUName","DTCCode","Description","FaultCategory","Status","OccurrenceCounter","AgingCounter","Priority","EventTimestamp","RiskScore"]
SIGNAL_COLUMNS = ["FileName","SW_I_Step","ECUName","DTCCode","SignalName","SignalValue","EventTimestamp"]

def _frame(records, columns):
    df = pd.DataFrame(records)
    for column in columns:
        if column not in df.columns: df[column] = pd.NA
    return df[columns + [c for c in df.columns if c not in columns]]

def build_data_quality_report(dtc_df):
    mandatory = ["SW_I_Step","ECUName","DTCCode","Description","FaultCategory","Status","OccurrenceCounter","AgingCounter","Priority","EventTimestamp"]
    total = len(dtc_df)
    return pd.DataFrame([{"Field": f, "MissingCount": int(dtc_df[f].isna().sum()) if f in dtc_df else total,
                          "MissingPercent": round(((int(dtc_df[f].isna().sum()) if f in dtc_df else total) / total * 100),2) if total else 0}
                         for f in mandatory], columns=["Field","MissingCount","MissingPercent"])

def build_correlation_candidates(dtc_df):
    columns=["EventDate","FaultCategory","ECUCount","DTCCount","ECUs","DTCs"]
    if dtc_df.empty: return pd.DataFrame(columns=columns)
    work=dtc_df.copy(); work["EventDate"]=pd.to_datetime(work["EventTimestamp"],errors="coerce").dt.date
    result=(work.dropna(subset=["EventDate"]).groupby(["EventDate","FaultCategory"],dropna=False)
            .agg(ECUCount=("ECUName","nunique"),DTCCount=("DTCCode","count"),
                 ECUs=("ECUName",lambda x:", ".join(sorted(set(x.dropna().astype(str))))),
                 DTCs=("DTCCode",lambda x:", ".join(sorted(set(x.dropna().astype(str)))))).reset_index())
    return result[result["ECUCount"]>=2].sort_values(["DTCCount","ECUCount"],ascending=False).reindex(columns=columns)

def build_summary_tables(report_df, ecu_df, dtc_df, env_df):
    if "EventTimestamp" in dtc_df: dtc_df["EventTimestamp"]=pd.to_datetime(dtc_df["EventTimestamp"],errors="coerce")
    executive=pd.DataFrame([{"FilesProcessed":report_df["FileName"].nunique() if not report_df.empty else 0,
        "ECUMetadataRecords":len(ecu_df),"ECUsWithDTCs":dtc_df["ECUName"].nunique() if not dtc_df.empty else 0,
        "DTCRecordCount":len(dtc_df),"UniqueDTCCount":dtc_df["DTCCode"].nunique() if not dtc_df.empty else 0,
        "EnvironmentSignalRecordCount":len(env_df),"EventDateRangeMin":dtc_df["EventTimestamp"].min() if not dtc_df.empty else None,
        "EventDateRangeMax":dtc_df["EventTimestamp"].max() if not dtc_df.empty else None}])
    if dtc_df.empty:
        return {"executive_summary":executive,"ecu_summary":pd.DataFrame(columns=["ECUName","DTCCount","UniqueDTCs","ActiveCount","StoredCount","IntermittentCount","TotalOccurrences","AveragePriority","MaxRiskScore"]),
        "status_summary":pd.DataFrame(columns=["Status","DTCCount"]),"category_summary":pd.DataFrame(columns=["FaultCategory","DTCCount","TotalOccurrences","ActiveCount","MaxRiskScore"]),
        "priority_summary":pd.DataFrame(columns=["Priority","DTCCount","TotalOccurrences"]),"top_risk_dtcs":dtc_df,"data_quality":build_data_quality_report(dtc_df)}
    for c in ["OccurrenceCounter","AgingCounter","Priority","RiskScore"]: dtc_df[c]=pd.to_numeric(dtc_df[c],errors="coerce")
    ecu=(dtc_df.groupby("ECUName").agg(DTCCount=("DTCCode","count"),UniqueDTCs=("DTCCode","nunique"),ActiveCount=("Status",lambda x:(x=="Active").sum()),StoredCount=("Status",lambda x:(x=="Stored").sum()),IntermittentCount=("Status",lambda x:(x=="Intermittent").sum()),TotalOccurrences=("OccurrenceCounter","sum"),AveragePriority=("Priority","mean"),MaxRiskScore=("RiskScore","max")).reset_index())
    status=dtc_df.groupby("Status").size().reset_index(name="DTCCount")
    category=dtc_df.groupby("FaultCategory").agg(DTCCount=("DTCCode","count"),TotalOccurrences=("OccurrenceCounter","sum"),ActiveCount=("Status",lambda x:(x=="Active").sum()),MaxRiskScore=("RiskScore","max")).reset_index()
    priority=dtc_df.groupby("Priority").agg(DTCCount=("DTCCode","count"),TotalOccurrences=("OccurrenceCounter","sum")).reset_index()
    return {"executive_summary":executive,"ecu_summary":ecu,"status_summary":status,"category_summary":category,"priority_summary":priority,"top_risk_dtcs":dtc_df.sort_values(["RiskScore","OccurrenceCounter"],ascending=False).head(25),"data_quality":build_data_quality_report(dtc_df)}

def csv_and_excel_file_export(reports, ecus, dtcs, signals, output_path, export_csv=True, export_excel=True):
    output_path=Path(output_path); report_df=_frame(reports,REPORT_COLUMNS); ecu_df=_frame(ecus,ECU_COLUMNS); dtc_df=_frame(dtcs,DTC_COLUMNS); env_df=_frame(signals,SIGNAL_COLUMNS)
    if "EventTimestamp" in dtc_df: dtc_df["EventTimestamp"]=pd.to_datetime(dtc_df["EventTimestamp"],errors="coerce")
    summary=build_summary_tables(report_df,ecu_df,dtc_df,env_df); correlation=build_correlation_candidates(dtc_df)
    outputs={"parsed_report_header":report_df,"parsed_ecu_metadata":ecu_df,"parsed_dtc_events":dtc_df,"parsed_environment_signals":env_df,
             "summary_ecu":summary["ecu_summary"],"summary_status":summary["status_summary"],"summary_fault_category":summary["category_summary"],
             "summary_priority":summary["priority_summary"],"data_quality_report":summary["data_quality"],"correlation_candidates":correlation}
    if export_csv:
        folder=output_path/"csv"; folder.mkdir(parents=True,exist_ok=True)
        for name,df in outputs.items(): df.to_csv(folder/f"{name}.csv",index=False)
    if export_excel:
        folder=output_path/"excel"; folder.mkdir(parents=True,exist_ok=True)
        with pd.ExcelWriter(folder/"Phase1_Diagnostic_Parser_Report.xlsx",engine="openpyxl") as writer:
            summary["executive_summary"].to_excel(writer,sheet_name="00_Executive_Summary",index=False)
            for sheet,df in [("01_Report_Header",report_df),("02_ECU_Metadata",ecu_df),("03_DTC_Events",dtc_df),("04_Environment_Signals",env_df),("05_ECU_Summary",summary["ecu_summary"]),("06_Status_Summary",summary["status_summary"]),("07_Category_Summary",summary["category_summary"]),("08_Priority_Summary",summary["priority_summary"]),("09_Top_Risk_DTCs",summary["top_risk_dtcs"]),("10_Data_Quality",summary["data_quality"]),("11_Correlation",correlation)]: df.to_excel(writer,sheet_name=sheet,index=False)
    return report_df,ecu_df,dtc_df,env_df,summary,correlation
