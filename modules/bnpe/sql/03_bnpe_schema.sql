-- Schéma minimal BNPE pour PostgreSQL/PostGIS
CREATE TABLE IF NOT EXISTS dim_ouvrage_prelevement (
    code_ouvrage text PRIMARY KEY,
    nom_ouvrage text,
    code_alternatif text,
    origine_code_alternatif text,
    departement text,
    code_insee text,
    commune text,
    lieu_dit text,
    type_eau text,
    longitude double precision,
    latitude double precision,
    precision_localisation text,
    code_bss text,
    code_zone_hydro text,
    nom_zone_hydro text,
    code_entite_hydro_cours_eau text,
    code_bdlisa text,
    libelle_bdlisa text,
    date_debut_exploitation text,
    date_fin_exploitation text
);

CREATE TABLE IF NOT EXISTS fact_prelevement_bnpe (
    annee_reference integer NOT NULL,
    code_ouvrage text NOT NULL REFERENCES dim_ouvrage_prelevement(code_ouvrage),
    code_usage_bnpe text NOT NULL,
    volume_m3 double precision,
    libelle_usage_bnpe text,
    code_usage_declare text,
    usage_declare text,
    type_eau text,
    mode_obtention_volume text,
    statut_volume text,
    qualification_volume text,
    source_file text,
    PRIMARY KEY (annee_reference, code_ouvrage, code_usage_bnpe)
);

CREATE TABLE IF NOT EXISTS fact_bnpe_synthese_usage (
    annee_reference integer NOT NULL,
    code_usage_bnpe text NOT NULL,
    volume_m3 double precision,
    proportion_pct double precision,
    PRIMARY KEY (annee_reference, code_usage_bnpe)
);

CREATE TABLE IF NOT EXISTS fact_bnpe_synthese_type_eau (
    annee_reference integer NOT NULL,
    type_eau text NOT NULL,
    volume_m3 double precision,
    proportion_pct double precision,
    PRIMARY KEY (annee_reference, type_eau)
);
