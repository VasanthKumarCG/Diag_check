CREATE OR REPLACE FUNCTION admin.run_data_quality_checks(p_process_run_id BIGINT,p_expected_signal_count INT DEFAULT 0)
RETURNS TABLE(process_run_id BIGINT,total_issues BIGINT,information_count BIGINT,warning_count BIGINT,error_count BIGINT,critical_count BIGINT,quality_status TEXT) LANGUAGE plpgsql AS $$
BEGIN
 DELETE FROM admin.data_quality_issue q WHERE q.process_run_id=p_process_run_id;
 INSERT INTO admin.data_quality_issue(process_run_id,file_id,source_table,source_row_id,rule_code,field_name,invalid_value,issue_description,severity)
 SELECT process_run_id,file_id,'stage.dtc_event',stage_dtc_event_id,'DQ001','ecu_name',ecu_name,'ECU is missing','Error' FROM stage.dtc_event WHERE process_run_id=p_process_run_id AND NULLIF(BTRIM(ecu_name),'') IS NULL;
 INSERT INTO admin.data_quality_issue(process_run_id,file_id,source_table,source_row_id,rule_code,field_name,invalid_value,issue_description,severity)
 SELECT process_run_id,file_id,'stage.dtc_event',stage_dtc_event_id,'DQ002','dtc_code',dtc_code,'DTC code is missing','Error' FROM stage.dtc_event WHERE process_run_id=p_process_run_id AND NULLIF(BTRIM(dtc_code),'') IS NULL;
 INSERT INTO admin.data_quality_issue(process_run_id,file_id,source_table,source_row_id,rule_code,field_name,invalid_value,issue_description,severity)
 SELECT process_run_id,file_id,'stage.dtc_event',stage_dtc_event_id,'DQ003','priority',priority::TEXT,'Priority outside 1 to 5','Error' FROM stage.dtc_event WHERE process_run_id=p_process_run_id AND (priority IS NULL OR priority NOT BETWEEN 1 AND 5);
 INSERT INTO admin.data_quality_issue(process_run_id,file_id,source_table,source_row_id,rule_code,field_name,invalid_value,issue_description,severity)
 SELECT process_run_id,file_id,'stage.dtc_event',stage_dtc_event_id,'DQ004','event_timestamp',NULL,'Timestamp missing or invalid','Error' FROM stage.dtc_event WHERE process_run_id=p_process_run_id AND event_timestamp IS NULL;
 RETURN QUERY SELECT p_process_run_id,COUNT(*)::BIGINT,COUNT(*) FILTER(WHERE severity='Information')::BIGINT,COUNT(*) FILTER(WHERE severity='Warning')::BIGINT,COUNT(*) FILTER(WHERE severity='Error')::BIGINT,COUNT(*) FILTER(WHERE severity='Critical')::BIGINT,CASE WHEN COUNT(*) FILTER(WHERE severity IN('Error','Critical'))=0 THEN 'Accepted' ELSE 'Rejected' END FROM admin.data_quality_issue WHERE process_run_id=p_process_run_id;
END $$;
