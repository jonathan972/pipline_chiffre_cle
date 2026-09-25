CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS ref_eau;
CREATE TABLE IF NOT EXISTS ref_eau.dim_perimeter(
 perimeter_id text PRIMARY KEY,label text NOT NULL,territory_kind text NOT NULL,authority text,operator text,
 valid_from date,valid_to date,notes text);
CREATE TABLE IF NOT EXISTS ref_eau.source_snapshot(
 snapshot_id bigserial PRIMARY KEY,source_family text NOT NULL,source_file text,source_url text,
 annee_reference integer,snapshot_date date,sha256 text,imported_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS ref_eau.fact_indicator(
 annee_reference integer NOT NULL,indicator_id text NOT NULL,domain text NOT NULL,territoire text NOT NULL,
 perimeter_id text,value numeric,unit text,numerator numeric,denominator numeric,source_primary text NOT NULL,
 source_detail text,source_file text,source_page integer,snapshot_date date,coverage_status text,quality_status text,
 record_role text NOT NULL,population_millesime integer,definition text,note text,imported_at timestamptz DEFAULT now());
CREATE INDEX IF NOT EXISTS idx_fact_indicator_year_domain ON ref_eau.fact_indicator(annee_reference,domain);
CREATE INDEX IF NOT EXISTS idx_fact_indicator_perimeter ON ref_eau.fact_indicator(perimeter_id,annee_reference);
CREATE TABLE IF NOT EXISTS ref_eau.run_log(
 run_id uuid PRIMARY KEY,started_at timestamptz NOT NULL,finished_at timestamptz,annee_reference integer NOT NULL,
 mode text NOT NULL,status text NOT NULL,manifest jsonb,message text);
