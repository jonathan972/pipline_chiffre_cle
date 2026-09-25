-- v6 : séparation stricte des territoires administratifs et des périmètres de service/contrat
CREATE TABLE IF NOT EXISTS dim_perimetre_service (
    perimeter_id text PRIMARY KEY,
    label text NOT NULL,
    territory_kind text NOT NULL,
    valid_from date,
    valid_to date,
    authority text,
    operator text,
    notes text,
    source_url text
);

CREATE TABLE IF NOT EXISTS bridge_perimetre_commune (
    perimeter_id text NOT NULL REFERENCES dim_perimetre_service(perimeter_id),
    commune_insee text NOT NULL,
    commune_name text NOT NULL,
    coverage_type text NOT NULL, -- FULL_COMMUNE / PARTIAL_COMMUNE
    sector_label text,
    valid_from date,
    valid_to date,
    PRIMARY KEY (perimeter_id, commune_insee, coverage_type, sector_label)
);

CREATE TABLE IF NOT EXISTS fact_source_anomaly (
    year_reference integer,
    object_id text,
    anomaly_type text,
    severity text,
    observation text,
    decision text,
    source_url text
);

-- Ne pas agréger les ratios entre périmètres par moyenne simple.
-- Les indicateurs hydrauliques P104.3/P105.3/P106.3 doivent conserver le perimeter_id
-- exact du bilan hydraulique qui a servi à leur calcul.
