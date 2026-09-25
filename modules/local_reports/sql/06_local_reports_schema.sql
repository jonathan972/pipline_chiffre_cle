CREATE TABLE IF NOT EXISTS fact_local_report (
    annee_reference integer NOT NULL,
    domain text NOT NULL,
    indicator_id text NOT NULL,
    territoire text NOT NULL,
    value numeric,
    unit text,
    source_family text NOT NULL,
    authority text,
    source_file text NOT NULL,
    source_page integer,
    record_role text NOT NULL DEFAULT 'PRODUCTION',
    quality_status text NOT NULL DEFAULT 'OK',
    coverage_status text NOT NULL DEFAULT 'COMPLETE',
    note text,
    numerator numeric,
    denominator numeric,
    imported_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_fact_local_report_key ON fact_local_report(annee_reference, domain, indicator_id, territoire);
