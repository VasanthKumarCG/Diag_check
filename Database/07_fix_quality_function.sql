-- Fix PL/pgSQL ambiguity between returned column names and table columns.
-- All table references are explicitly qualified with aliases.

CREATE OR REPLACE FUNCTION admin.run_data_quality_checks(
    p_process_run_id BIGINT,
    p_expected_signal_count INTEGER DEFAULT 0
)
RETURNS TABLE (
    process_run_id BIGINT,
    total_issues BIGINT,
    information_count BIGINT,
    warning_count BIGINT,
    error_count BIGINT,
    critical_count BIGINT,
    quality_status TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM admin.data_quality_issue AS q
    WHERE q.process_run_id = p_process_run_id;

    -- DQ001: Missing ECU name
    INSERT INTO admin.data_quality_issue (
        process_run_id,
        file_id,
        source_table,
        source_row_id,
        rule_code,
        field_name,
        invalid_value,
        issue_description,
        severity
    )
    SELECT
        d.process_run_id,
        d.file_id,
        'stage.dtc_event',
        d.stage_dtc_event_id,
        'DQ001',
        'ecu_name',
        d.ecu_name,
        'ECU is missing.',
        'Error'
    FROM stage.dtc_event AS d
    WHERE d.process_run_id = p_process_run_id
      AND NULLIF(BTRIM(d.ecu_name), '') IS NULL;

    -- DQ002: Missing or malformed DTC code
    INSERT INTO admin.data_quality_issue (
        process_run_id,
        file_id,
        source_table,
        source_row_id,
        rule_code,
        field_name,
        invalid_value,
        issue_description,
        severity
    )
    SELECT
        d.process_run_id,
        d.file_id,
        'stage.dtc_event',
        d.stage_dtc_event_id,
        'DQ002',
        'dtc_code',
        d.dtc_code,
        'DTC code is missing or malformed.',
        'Error'
    FROM stage.dtc_event AS d
    WHERE d.process_run_id = p_process_run_id
      AND (
          NULLIF(BTRIM(d.dtc_code), '') IS NULL
          OR UPPER(d.dtc_code) !~ '^0X[0-9A-F]+$'
      );

    -- DQ003: Invalid priority
    INSERT INTO admin.data_quality_issue (
        process_run_id,
        file_id,
        source_table,
        source_row_id,
        rule_code,
        field_name,
        invalid_value,
        issue_description,
        severity
    )
    SELECT
        d.process_run_id,
        d.file_id,
        'stage.dtc_event',
        d.stage_dtc_event_id,
        'DQ003',
        'priority',
        d.priority::TEXT,
        'Priority is missing or outside the allowed range 1 to 5.',
        'Error'
    FROM stage.dtc_event AS d
    WHERE d.process_run_id = p_process_run_id
      AND (
          d.priority IS NULL
          OR d.priority NOT BETWEEN 1 AND 5
      );

    -- DQ004: Missing or invalid event timestamp
    INSERT INTO admin.data_quality_issue (
        process_run_id,
        file_id,
        source_table,
        source_row_id,
        rule_code,
        field_name,
        invalid_value,
        issue_description,
        severity
    )
    SELECT
        d.process_run_id,
        d.file_id,
        'stage.dtc_event',
        d.stage_dtc_event_id,
        'DQ004',
        'event_timestamp',
        NULL,
        'Event timestamp is missing or invalid.',
        'Error'
    FROM stage.dtc_event AS d
    WHERE d.process_run_id = p_process_run_id
      AND d.event_timestamp IS NULL;

    -- DQ005: Unsupported status
    INSERT INTO admin.data_quality_issue (
        process_run_id,
        file_id,
        source_table,
        source_row_id,
        rule_code,
        field_name,
        invalid_value,
        issue_description,
        severity
    )
    SELECT
        d.process_run_id,
        d.file_id,
        'stage.dtc_event',
        d.stage_dtc_event_id,
        'DQ005',
        'status',
        d.status,
        'Unsupported DTC status.',
        'Error'
    FROM stage.dtc_event AS d
    WHERE d.process_run_id = p_process_run_id
      AND COALESCE(d.status, '') NOT IN (
          'Active',
          'Stored',
          'Intermittent',
          'Pending'
      );

    -- DQ006: Invalid occurrence counter
    INSERT INTO admin.data_quality_issue (
        process_run_id,
        file_id,
        source_table,
        source_row_id,
        rule_code,
        field_name,
        invalid_value,
        issue_description,
        severity
    )
    SELECT
        d.process_run_id,
        d.file_id,
        'stage.dtc_event',
        d.stage_dtc_event_id,
        'DQ006',
        'occurrence_counter',
        d.occurrence_counter::TEXT,
        'Occurrence counter is missing or negative.',
        'Error'
    FROM stage.dtc_event AS d
    WHERE d.process_run_id = p_process_run_id
      AND (
          d.occurrence_counter IS NULL
          OR d.occurrence_counter < 0
      );

    -- DQ007: Invalid aging counter
    INSERT INTO admin.data_quality_issue (
        process_run_id,
        file_id,
        source_table,
        source_row_id,
        rule_code,
        field_name,
        invalid_value,
        issue_description,
        severity
    )
    SELECT
        d.process_run_id,
        d.file_id,
        'stage.dtc_event',
        d.stage_dtc_event_id,
        'DQ007',
        'aging_counter',
        d.aging_counter::TEXT,
        'Aging counter is missing or negative.',
        'Error'
    FROM stage.dtc_event AS d
    WHERE d.process_run_id = p_process_run_id
      AND (
          d.aging_counter IS NULL
          OR d.aging_counter < 0
      );

    -- DQ008: Detection dates are reversed
    INSERT INTO admin.data_quality_issue (
        process_run_id,
        file_id,
        source_table,
        source_row_id,
        rule_code,
        field_name,
        invalid_value,
        issue_description,
        severity
    )
    SELECT
        d.process_run_id,
        d.file_id,
        'stage.dtc_event',
        d.stage_dtc_event_id,
        'DQ008',
        'first_detected',
        d.first_detected::TEXT,
        'FirstDetected occurs after LastDetected.',
        'Warning'
    FROM stage.dtc_event AS d
    WHERE d.process_run_id = p_process_run_id
      AND d.first_detected IS NOT NULL
      AND d.last_detected IS NOT NULL
      AND d.first_detected > d.last_detected;

    -- DQ009: Expected signal count differs
    -- Applied only when EXPECTED_SIGNALS_PER_DTC is greater than zero.
    INSERT INTO admin.data_quality_issue (
        process_run_id,
        file_id,
        source_table,
        source_row_id,
        rule_code,
        field_name,
        invalid_value,
        issue_description,
        severity
    )
    SELECT
        d.process_run_id,
        d.file_id,
        'stage.environment_signal',
        d.stage_dtc_event_id,
        'DQ009',
        'environment_signal_count',
        COUNT(s.stage_signal_id)::TEXT,
        FORMAT(
            'Expected %s environment signals but found %s.',
            p_expected_signal_count,
            COUNT(s.stage_signal_id)
        ),
        'Warning'
    FROM stage.dtc_event AS d
    LEFT JOIN stage.environment_signal AS s
        ON s.process_run_id = d.process_run_id
       AND s.file_id = d.file_id
       AND s.ecu_name = d.ecu_name
       AND UPPER(s.dtc_code) = UPPER(d.dtc_code)
       AND s.event_timestamp = d.event_timestamp
    WHERE d.process_run_id = p_process_run_id
      AND p_expected_signal_count > 0
    GROUP BY
        d.process_run_id,
        d.file_id,
        d.stage_dtc_event_id
    HAVING COUNT(s.stage_signal_id) <> p_expected_signal_count;

    RETURN QUERY
    SELECT
        p_process_run_id AS process_run_id,
        COUNT(q.quality_issue_id)::BIGINT AS total_issues,
        COUNT(q.quality_issue_id)
            FILTER (WHERE q.severity = 'Information')::BIGINT
            AS information_count,
        COUNT(q.quality_issue_id)
            FILTER (WHERE q.severity = 'Warning')::BIGINT
            AS warning_count,
        COUNT(q.quality_issue_id)
            FILTER (WHERE q.severity = 'Error')::BIGINT
            AS error_count,
        COUNT(q.quality_issue_id)
            FILTER (WHERE q.severity = 'Critical')::BIGINT
            AS critical_count,
        CASE
            WHEN COUNT(q.quality_issue_id)
                FILTER (
                    WHERE q.severity IN ('Error', 'Critical')
                ) = 0
            THEN 'Accepted'
            ELSE 'Rejected'
        END AS quality_status
    FROM admin.data_quality_issue AS q
    WHERE q.process_run_id = p_process_run_id;
END;
$$;