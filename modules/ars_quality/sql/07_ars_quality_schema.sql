CREATE SCHEMA IF NOT EXISTS ref_eau;
CREATE TABLE IF NOT EXISTS ref_eau.fact_ars_quality (
 annee_reference integer NOT NULL, indicator_id text NOT NULL, territoire text NOT NULL,
 perimeter_id text, value numeric, unit text, numerator numeric, denominator numeric,
 source_primary text, source_detail text, coverage_status text, quality_status text,
 record_role text, definition text, note text, imported_at timestamptz DEFAULT now(),
 PRIMARY KEY (annee_reference,indicator_id,territoire)
);