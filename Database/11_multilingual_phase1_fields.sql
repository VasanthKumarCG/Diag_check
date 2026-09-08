-- Canonical and source-language evidence fields.
ALTER TABLE stage.dtc_event ADD COLUMN IF NOT EXISTS source_language VARCHAR(20) NOT NULL DEFAULT 'en';
ALTER TABLE stage.dtc_event ADD COLUMN IF NOT EXISTS source_possible_cause TEXT;
ALTER TABLE stage.dtc_event ADD COLUMN IF NOT EXISTS source_recommended_check TEXT;
ALTER TABLE raw.dtc_event ADD COLUMN IF NOT EXISTS source_language VARCHAR(20) NOT NULL DEFAULT 'en';
ALTER TABLE raw.dtc_event ADD COLUMN IF NOT EXISTS source_possible_cause TEXT;
ALTER TABLE raw.dtc_event ADD COLUMN IF NOT EXISTS source_recommended_check TEXT;
CREATE INDEX IF NOT EXISTS ix_raw_dtc_source_language ON raw.dtc_event(source_language);
