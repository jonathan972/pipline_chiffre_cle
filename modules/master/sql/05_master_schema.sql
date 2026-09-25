CREATE TABLE IF NOT EXISTS fact_indicateur_master (
    annee_reference smallint NOT NULL,
    indicator_id text NOT NULL,
    domain text NOT NULL,
    territoire text NOT NULL,
    value double precision,
    unit text,
    source_primary text,
    source_detail text,
    source_file text,
    snapshot_date text,
    coverage_status text,
    quality_status text,
    record_role text,
    population_millesime smallint,
    note text,
    PRIMARY KEY (annee_reference, indicator_id, territoire, record_role)
);
