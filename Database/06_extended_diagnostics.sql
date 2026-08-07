-- Cross-verification extension based on Phase1_Diagnostic_Parser_Report.xlsx.
-- Keeps frequently queried diagnostics as typed columns and all other future fields in JSONB.
ALTER TABLE stage.dtc_event ADD COLUMN IF NOT EXISTS normalized_fault_category VARCHAR(100);
ALTER TABLE stage.dtc_event ADD COLUMN IF NOT EXISTS healing_counter INT;
ALTER TABLE stage.dtc_event ADD COLUMN IF NOT EXISTS debounce_counter INT;
ALTER TABLE stage.dtc_event ADD COLUMN IF NOT EXISTS severity VARCHAR(30);
ALTER TABLE stage.dtc_event ADD COLUMN IF NOT EXISTS first_detected TIMESTAMPTZ;
ALTER TABLE stage.dtc_event ADD COLUMN IF NOT EXISTS last_detected TIMESTAMPTZ;
ALTER TABLE stage.dtc_event ADD COLUMN IF NOT EXISTS confirmation_state VARCHAR(100);
ALTER TABLE stage.dtc_event ADD COLUMN IF NOT EXISTS possible_cause TEXT;
ALTER TABLE stage.dtc_event ADD COLUMN IF NOT EXISTS recommended_check TEXT;
ALTER TABLE stage.dtc_event ADD COLUMN IF NOT EXISTS extended_attributes JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE raw.dtc_event ADD COLUMN IF NOT EXISTS normalized_fault_category VARCHAR(100);
ALTER TABLE raw.dtc_event ADD COLUMN IF NOT EXISTS healing_counter INT;
ALTER TABLE raw.dtc_event ADD COLUMN IF NOT EXISTS debounce_counter INT;
ALTER TABLE raw.dtc_event ADD COLUMN IF NOT EXISTS severity VARCHAR(30);
ALTER TABLE raw.dtc_event ADD COLUMN IF NOT EXISTS first_detected TIMESTAMPTZ;
ALTER TABLE raw.dtc_event ADD COLUMN IF NOT EXISTS last_detected TIMESTAMPTZ;
ALTER TABLE raw.dtc_event ADD COLUMN IF NOT EXISTS confirmation_state VARCHAR(100);
ALTER TABLE raw.dtc_event ADD COLUMN IF NOT EXISTS possible_cause TEXT;
ALTER TABLE raw.dtc_event ADD COLUMN IF NOT EXISTS recommended_check TEXT;
ALTER TABLE raw.dtc_event ADD COLUMN IF NOT EXISTS extended_attributes JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE raw.dtc_event DROP CONSTRAINT IF EXISTS raw_dtc_event_status_check;
ALTER TABLE raw.dtc_event DROP CONSTRAINT IF EXISTS dtc_event_status_check;
ALTER TABLE raw.dtc_event ADD CONSTRAINT dtc_event_status_check CHECK(status IN('Active','Stored','Intermittent','Pending'));
CREATE INDEX IF NOT EXISTS ix_raw_dtc_severity ON raw.dtc_event(severity);
CREATE INDEX IF NOT EXISTS ix_raw_dtc_confirmation ON raw.dtc_event(confirmation_state);
CREATE INDEX IF NOT EXISTS ix_raw_dtc_extended_gin ON raw.dtc_event USING GIN(extended_attributes);

CREATE OR REPLACE FUNCTION admin.run_data_quality_checks(p_process_run_id BIGINT,p_expected_signal_count INT DEFAULT 0)
RETURNS TABLE(process_run_id BIGINT,total_issues BIGINT,information_count BIGINT,warning_count BIGINT,error_count BIGINT,critical_count BIGINT,quality_status TEXT) LANGUAGE plpgsql AS $$
BEGIN
 DELETE FROM admin.data_quality_issue q WHERE q.process_run_id=p_process_run_id;
 INSERT INTO admin.data_quality_issue(process_run_id,file_id,source_table,source_row_id,rule_code,field_name,invalid_value,issue_description,severity)
 SELECT process_run_id,file_id,'stage.dtc_event',stage_dtc_event_id,'DQ001','ecu_name',ecu_name,'ECU is missing','Error' FROM stage.dtc_event WHERE process_run_id=p_process_run_id AND NULLIF(BTRIM(ecu_name),'') IS NULL;
 INSERT INTO admin.data_quality_issue(process_run_id,file_id,source_table,source_row_id,rule_code,field_name,invalid_value,issue_description,severity)
 SELECT process_run_id,file_id,'stage.dtc_event',stage_dtc_event_id,'DQ002','dtc_code',dtc_code,'DTC code is missing or malformed','Error' FROM stage.dtc_event WHERE process_run_id=p_process_run_id AND (NULLIF(BTRIM(dtc_code),'') IS NULL OR UPPER(dtc_code)!~'^0X[0-9A-F]+$');
 INSERT INTO admin.data_quality_issue(process_run_id,file_id,source_table,source_row_id,rule_code,field_name,invalid_value,issue_description,severity)
 SELECT process_run_id,file_id,'stage.dtc_event',stage_dtc_event_id,'DQ003','priority',priority::TEXT,'Priority outside 1 to 5','Error' FROM stage.dtc_event WHERE process_run_id=p_process_run_id AND (priority IS NULL OR priority NOT BETWEEN 1 AND 5);
 INSERT INTO admin.data_quality_issue(process_run_id,file_id,source_table,source_row_id,rule_code,field_name,invalid_value,issue_description,severity)
 SELECT process_run_id,file_id,'stage.dtc_event',stage_dtc_event_id,'DQ004','event_timestamp',NULL,'Timestamp missing or invalid','Error' FROM stage.dtc_event WHERE process_run_id=p_process_run_id AND event_timestamp IS NULL;
 INSERT INTO admin.data_quality_issue(process_run_id,file_id,source_table,source_row_id,rule_code,field_name,invalid_value,issue_description,severity)
 SELECT process_run_id,file_id,'stage.dtc_event',stage_dtc_event_id,'DQ005','status',status,'Unsupported DTC status','Error' FROM stage.dtc_event WHERE process_run_id=p_process_run_id AND COALESCE(status,'') NOT IN('Active','Stored','Intermittent','Pending');
 INSERT INTO admin.data_quality_issue(process_run_id,file_id,source_table,source_row_id,rule_code,field_name,invalid_value,issue_description,severity)
 SELECT process_run_id,file_id,'stage.dtc_event',stage_dtc_event_id,'DQ006','occurrence_counter',occurrence_counter::TEXT,'Occurrence counter is negative or missing','Error' FROM stage.dtc_event WHERE process_run_id=p_process_run_id AND (occurrence_counter IS NULL OR occurrence_counter<0);
 INSERT INTO admin.data_quality_issue(process_run_id,file_id,source_table,source_row_id,rule_code,field_name,invalid_value,issue_description,severity)
 SELECT process_run_id,file_id,'stage.dtc_event',stage_dtc_event_id,'DQ007','aging_counter',aging_counter::TEXT,'Aging counter is negative or missing','Error' FROM stage.dtc_event WHERE process_run_id=p_process_run_id AND (aging_counter IS NULL OR aging_counter<0);
 INSERT INTO admin.data_quality_issue(process_run_id,file_id,source_table,source_row_id,rule_code,field_name,invalid_value,issue_description,severity)
 SELECT process_run_id,file_id,'stage.dtc_event',stage_dtc_event_id,'DQ008','first_detected',first_detected::TEXT,'First detected is after last detected','Warning' FROM stage.dtc_event WHERE process_run_id=p_process_run_id AND first_detected IS NOT NULL AND last_detected IS NOT NULL AND first_detected>last_detected;
 RETURN QUERY SELECT p_process_run_id,COUNT(*)::BIGINT,COUNT(*) FILTER(WHERE severity='Information')::BIGINT,COUNT(*) FILTER(WHERE severity='Warning')::BIGINT,COUNT(*) FILTER(WHERE severity='Error')::BIGINT,COUNT(*) FILTER(WHERE severity='Critical')::BIGINT,CASE WHEN COUNT(*) FILTER(WHERE severity IN('Error','Critical'))=0 THEN 'Accepted' ELSE 'Rejected' END FROM admin.data_quality_issue WHERE process_run_id=p_process_run_id;
END $$;

CREATE OR REPLACE PROCEDURE admin.promote_process_run(p_process_run_id BIGINT) LANGUAGE plpgsql AS $$
DECLARE v_file_id BIGINT; v_report_id BIGINT; v_errors BIGINT;
BEGIN
 SELECT file_id INTO STRICT v_file_id FROM admin.process_execution_log WHERE process_run_id=p_process_run_id;
 SELECT COUNT(*) INTO v_errors FROM admin.data_quality_issue WHERE process_run_id=p_process_run_id AND severity IN('Error','Critical');
 IF v_errors>0 THEN RAISE EXCEPTION 'Run % has % blocking issues',p_process_run_id,v_errors; END IF;
 INSERT INTO raw.diagnostic_report(file_id,file_name,file_path,vin,sw_i_step,sa_codes) SELECT file_id,file_name,file_path,vin,sw_i_step,sa_codes FROM stage.diagnostic_report WHERE process_run_id=p_process_run_id ON CONFLICT(file_id) DO UPDATE SET file_path=EXCLUDED.file_path,vin=EXCLUDED.vin,sw_i_step=EXCLUDED.sw_i_step,sa_codes=EXCLUDED.sa_codes RETURNING report_id INTO v_report_id;
 INSERT INTO raw.ecu_version(report_id,ecu_name,hardware_version,bootloader_version,sw_version,coding,diagnostic_address,calibration_version,network,secure_boot,ota_state) SELECT v_report_id,ecu_name,hardware_version,bootloader_version,sw_version,coding,diagnostic_address,calibration_version,network,secure_boot,ota_state FROM stage.ecu_version WHERE process_run_id=p_process_run_id AND NULLIF(BTRIM(ecu_name),'') IS NOT NULL ON CONFLICT(report_id,ecu_name) DO UPDATE SET hardware_version=EXCLUDED.hardware_version,bootloader_version=EXCLUDED.bootloader_version,sw_version=EXCLUDED.sw_version,coding=EXCLUDED.coding,diagnostic_address=EXCLUDED.diagnostic_address,calibration_version=EXCLUDED.calibration_version,network=EXCLUDED.network,secure_boot=EXCLUDED.secure_boot,ota_state=EXCLUDED.ota_state;
 INSERT INTO raw.dtc_event(report_id,source_row_number,ecu_name,dtc_code,description,fault_category,normalized_fault_category,status,occurrence_counter,aging_counter,priority,healing_counter,debounce_counter,severity,first_detected,last_detected,confirmation_state,possible_cause,recommended_check,event_timestamp,risk_score,extended_attributes)
 SELECT v_report_id,source_row_number,ecu_name,UPPER(dtc_code),description,fault_category,normalized_fault_category,status,occurrence_counter,aging_counter,priority,healing_counter,debounce_counter,severity,first_detected,last_detected,confirmation_state,possible_cause,recommended_check,event_timestamp,risk_score,extended_attributes FROM stage.dtc_event WHERE process_run_id=p_process_run_id
 ON CONFLICT(report_id,source_row_number) DO UPDATE SET ecu_name=EXCLUDED.ecu_name,dtc_code=EXCLUDED.dtc_code,description=EXCLUDED.description,fault_category=EXCLUDED.fault_category,normalized_fault_category=EXCLUDED.normalized_fault_category,status=EXCLUDED.status,occurrence_counter=EXCLUDED.occurrence_counter,aging_counter=EXCLUDED.aging_counter,priority=EXCLUDED.priority,healing_counter=EXCLUDED.healing_counter,debounce_counter=EXCLUDED.debounce_counter,severity=EXCLUDED.severity,first_detected=EXCLUDED.first_detected,last_detected=EXCLUDED.last_detected,confirmation_state=EXCLUDED.confirmation_state,possible_cause=EXCLUDED.possible_cause,recommended_check=EXCLUDED.recommended_check,event_timestamp=EXCLUDED.event_timestamp,risk_score=EXCLUDED.risk_score,extended_attributes=EXCLUDED.extended_attributes;
 INSERT INTO raw.environment_signal(dtc_event_id,source_row_number,signal_name,signal_value,numeric_signal_value,event_timestamp) SELECT d.dtc_event_id,s.source_row_number,s.signal_name,s.signal_value,CASE WHEN BTRIM(s.signal_value)~'^-?[0-9]+([.][0-9]+)?$' THEN BTRIM(s.signal_value)::NUMERIC(18,4) END,s.event_timestamp FROM stage.environment_signal s JOIN raw.dtc_event d ON d.report_id=v_report_id AND d.ecu_name=s.ecu_name AND d.dtc_code=UPPER(s.dtc_code) AND d.event_timestamp=s.event_timestamp WHERE s.process_run_id=p_process_run_id AND NULLIF(BTRIM(s.signal_name),'') IS NOT NULL ON CONFLICT(dtc_event_id,source_row_number) DO UPDATE SET signal_name=EXCLUDED.signal_name,signal_value=EXCLUDED.signal_value,numeric_signal_value=EXCLUDED.numeric_signal_value,event_timestamp=EXCLUDED.event_timestamp;
 UPDATE admin.process_execution_log SET end_time=CURRENT_TIMESTAMP,files_processed=1,report_records_loaded=(SELECT COUNT(*) FROM stage.diagnostic_report WHERE process_run_id=p_process_run_id),ecu_records_loaded=(SELECT COUNT(*) FROM stage.ecu_version WHERE process_run_id=p_process_run_id),dtc_records_loaded=(SELECT COUNT(*) FROM stage.dtc_event WHERE process_run_id=p_process_run_id),environment_records_loaded=(SELECT COUNT(*) FROM stage.environment_signal WHERE process_run_id=p_process_run_id),process_status='Completed' WHERE process_run_id=p_process_run_id;
 UPDATE admin.file_inventory SET processing_end_time=CURRENT_TIMESTAMP,process_status='Completed' WHERE file_id=v_file_id;
END $$;

CREATE OR REPLACE VIEW reporting.vw_extended_dtc_detail AS
SELECT
    r.report_id,
    r.file_id,
    r.file_name,
    r.file_path,
    r.vin,
    r.sw_i_step,
    r.sa_codes,
    r.created_datetime AS report_created_datetime,

    d.dtc_event_id,
    d.source_row_number,
    d.ecu_name,
    d.dtc_code,
    d.description,
    d.fault_category,
    d.normalized_fault_category,
    d.status,
    d.occurrence_counter,
    d.aging_counter,
    d.priority,
    d.healing_counter,
    d.debounce_counter,
    d.severity,
    d.first_detected,
    d.last_detected,
    d.confirmation_state,
    d.possible_cause,
    d.recommended_check,
    d.event_timestamp,
    d.risk_score,
    d.extended_attributes,

    e.ecu_version_id,
    e.hardware_version,
    e.bootloader_version,
    e.sw_version,
    e.coding,
    e.diagnostic_address,
    e.calibration_version,
    e.network,
    e.secure_boot,
    e.ota_state
FROM raw.diagnostic_report AS r
JOIN raw.dtc_event AS d
    ON d.report_id = r.report_id
LEFT JOIN raw.ecu_version AS e
    ON e.report_id = r.report_id
   AND e.ecu_name = d.ecu_name;
CREATE OR REPLACE VIEW reporting.vw_severity_summary AS SELECT r.sw_i_step,COALESCE(d.severity,'Unspecified') severity,COUNT(*) dtc_count,COUNT(*) FILTER(WHERE d.status='Active') active_count,MAX(d.risk_score) max_risk_score FROM raw.dtc_event d JOIN raw.diagnostic_report r ON r.report_id=d.report_id GROUP BY r.sw_i_step,COALESCE(d.severity,'Unspecified');
CREATE OR REPLACE VIEW reporting.vw_confirmation_summary AS SELECT r.sw_i_step,COALESCE(d.confirmation_state,'Unspecified') confirmation_state,COUNT(*) dtc_count,COUNT(*) FILTER(WHERE d.status='Active') active_count FROM raw.dtc_event d JOIN raw.diagnostic_report r ON r.report_id=d.report_id GROUP BY r.sw_i_step,COALESCE(d.confirmation_state,'Unspecified');
