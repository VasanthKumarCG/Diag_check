-- Level 2 knowledge and vector retrieval extension.
-- Requires the pgvector server extension to be installed.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS knowledge;

CREATE TABLE IF NOT EXISTS knowledge.document (
    document_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN ('RCA','JIRA','RELEASE_NOTE','DTC_DOC','KNOWN_ISSUE','ECU_ARCH')),
    source_id VARCHAR(200),
    source_name VARCHAR(500) NOT NULL,
    source_uri TEXT,
    content_sha256 CHAR(64) NOT NULL UNIQUE,
    vehicle_model VARCHAR(100),
    vin_scope VARCHAR(30),
    sw_release VARCHAR(100),
    sw_variant VARCHAR(100),
    build_date DATE,
    primary_ecu VARCHAR(100),
    related_ecus TEXT[] NOT NULL DEFAULT '{}',
    dtc_codes TEXT[] NOT NULL DEFAULT '{}',
    approval_status VARCHAR(30) NOT NULL DEFAULT 'Draft' CHECK (approval_status IN ('Draft','Approved','Rejected','Superseded')),
    approved_by VARCHAR(200),
    approved_at TIMESTAMPTZ,
    root_cause TEXT,
    corrective_action TEXT,
    fix_release VARCHAR(100),
    validation_result TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge.chunk (
    chunk_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES knowledge.document(document_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    token_estimate INTEGER,
    chunk_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding VECTOR(1024) NOT NULL,
    embedding_model VARCHAR(200) NOT NULL,
    embedding_dimension INTEGER NOT NULL DEFAULT 1024 CHECK (embedding_dimension = 1024),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (document_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS knowledge.retrieval_audit (
    retrieval_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    query_id UUID NOT NULL,
    query_text TEXT NOT NULL,
    query_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    chunk_id BIGINT REFERENCES knowledge.chunk(chunk_id),
    rank_number INTEGER,
    distance DOUBLE PRECISION,
    embedding_model VARCHAR(200),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge.ai_analysis (
    analysis_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    query_id UUID NOT NULL UNIQUE,
    report_id BIGINT REFERENCES raw.diagnostic_report(report_id),
    dtc_event_id BIGINT REFERENCES raw.dtc_event(dtc_event_id),
    model_name VARCHAR(200) NOT NULL,
    prompt_version VARCHAR(50) NOT NULL,
    case_summary TEXT,
    response_json JSONB NOT NULL,
    engineering_confirmation_required BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge.engineer_feedback (
    feedback_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    analysis_id BIGINT NOT NULL REFERENCES knowledge.ai_analysis(analysis_id) ON DELETE CASCADE,
    decision VARCHAR(30) NOT NULL CHECK (decision IN ('Accepted','PartiallyAccepted','Rejected')),
    confirmed_root_cause TEXT,
    confirmed_fix TEXT,
    confirmed_fix_release VARCHAR(100),
    usefulness_score SMALLINT CHECK (usefulness_score BETWEEN 1 AND 5),
    comments TEXT,
    reviewed_by VARCHAR(200) NOT NULL,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_document_source_type ON knowledge.document(source_type);
CREATE INDEX IF NOT EXISTS ix_document_release_ecu ON knowledge.document(sw_release, primary_ecu);
CREATE INDEX IF NOT EXISTS ix_document_dtc_codes_gin ON knowledge.document USING GIN(dtc_codes);
CREATE INDEX IF NOT EXISTS ix_document_related_ecus_gin ON knowledge.document USING GIN(related_ecus);
CREATE INDEX IF NOT EXISTS ix_document_metadata_gin ON knowledge.document USING GIN(metadata);
CREATE INDEX IF NOT EXISTS ix_chunk_document_id ON knowledge.chunk(document_id);
-- Start with exact search for the small POC. Add HNSW after sufficient chunk volume and measurement.
