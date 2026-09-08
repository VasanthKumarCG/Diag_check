-- Reference and deterministic correlation structures for Level 2/3.
CREATE SCHEMA IF NOT EXISTS reference;
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS reference.software_release (
    sw_release VARCHAR(100) PRIMARY KEY,
    release_sequence INTEGER NOT NULL UNIQUE,
    release_date DATE,
    vehicle_model VARCHAR(100),
    sw_variant VARCHAR(100),
    release_type VARCHAR(50),
    baseline_release BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS reference.ecu_relationship (
    relationship_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_ecu VARCHAR(100) NOT NULL,
    target_ecu VARCHAR(100) NOT NULL,
    interaction_type VARCHAR(100) NOT NULL,
    network VARCHAR(100),
    direction VARCHAR(30) NOT NULL DEFAULT 'Bidirectional' CHECK (direction IN ('SourceToTarget','TargetToSource','Bidirectional')),
    criticality VARCHAR(30) NOT NULL DEFAULT 'Medium' CHECK (criticality IN ('Critical','High','Medium','Low')),
    valid_from_release VARCHAR(100),
    valid_to_release VARCHAR(100),
    approved_by VARCHAR(200),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE(source_ecu, target_ecu, interaction_type, valid_from_release)
);

CREATE TABLE IF NOT EXISTS reference.ecu_owner (
    ecu_name VARCHAR(100) PRIMARY KEY,
    department VARCHAR(200),
    team_name VARCHAR(200),
    owner_name VARCHAR(200),
    contact_email VARCHAR(320),
    escalation_path TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS reference.risk_threshold (
    threshold_name VARCHAR(100) PRIMARY KEY,
    lower_bound NUMERIC NOT NULL,
    upper_bound NUMERIC,
    risk_band VARCHAR(30) NOT NULL,
    response_sla_hours INTEGER,
    approved_by VARCHAR(200),
    approved_at TIMESTAMPTZ,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS analytics.correlation_run (
    correlation_run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    report_id BIGINT NOT NULL REFERENCES raw.diagnostic_report(report_id),
    event_window_seconds INTEGER NOT NULL,
    algorithm_version VARCHAR(50) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    status VARCHAR(30) NOT NULL DEFAULT 'Started' CHECK (status IN ('Started','Completed','Failed')),
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS analytics.correlation_candidate (
    correlation_candidate_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    correlation_run_id BIGINT NOT NULL REFERENCES analytics.correlation_run(correlation_run_id) ON DELETE CASCADE,
    primary_dtc_event_id BIGINT REFERENCES raw.dtc_event(dtc_event_id),
    related_dtc_event_id BIGINT REFERENCES raw.dtc_event(dtc_event_id),
    primary_ecu VARCHAR(100) NOT NULL,
    related_ecu VARCHAR(100) NOT NULL,
    time_delta_seconds NUMERIC(12,3),
    rule_codes TEXT[] NOT NULL DEFAULT '{}',
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    score NUMERIC(8,4) NOT NULL,
    classification VARCHAR(50) NOT NULL DEFAULT 'Candidate',
    engineering_confirmation_required BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE VIEW reporting.vw_release_regression AS
WITH release_dtc AS (
    SELECT
        r.sw_i_step AS sw_release,
        d.ecu_name,
        d.dtc_code,
        COUNT(*) AS dtc_events,
        COUNT(DISTINCT r.file_id) AS affected_reports,
        SUM(d.occurrence_counter) AS total_occurrences
    FROM raw.diagnostic_report r
    JOIN raw.dtc_event d ON d.report_id = r.report_id
    GROUP BY r.sw_i_step, d.ecu_name, d.dtc_code
), ordered AS (
    SELECT
        x.*,
        ref.release_sequence,
        LAG(x.dtc_events) OVER (PARTITION BY x.ecu_name, x.dtc_code ORDER BY ref.release_sequence) AS previous_dtc_events,
        LAG(x.affected_reports) OVER (PARTITION BY x.ecu_name, x.dtc_code ORDER BY ref.release_sequence) AS previous_affected_reports
    FROM release_dtc x
    JOIN reference.software_release ref ON ref.sw_release = x.sw_release
)
SELECT
    *,
    dtc_events::NUMERIC / NULLIF(affected_reports,0) AS dtcs_per_affected_report,
    CASE
        WHEN previous_dtc_events IS NULL THEN 'First observed'
        WHEN previous_dtc_events = 0 THEN 'New candidate'
        WHEN dtc_events >= previous_dtc_events * 3 AND affected_reports >= 3 THEN 'Suspected regression'
        WHEN dtc_events < previous_dtc_events THEN 'Improved candidate'
        ELSE 'Stable/monitor'
    END AS regression_classification
FROM ordered;
