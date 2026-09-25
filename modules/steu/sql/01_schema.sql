-- Schéma minimal pour le prototype STEU.
-- À intégrer ensuite au référentiel global Observatoire Eau & Assainissement.

CREATE SCHEMA IF NOT EXISTS ode_ref;
CREATE SCHEMA IF NOT EXISTS ode_fact;
CREATE SCHEMA IF NOT EXISTS ode_etl;

CREATE TABLE IF NOT EXISTS ode_ref.dim_steu (
    code_steu text PRIMARY KEY,
    nom_steu text,
    nature_steu text,
    code_sandre_nature_steu text,
    commune_implantation text,
    code_insee_commune text,
    maitre_ouvrage text,
    exploitant text,
    epci_normalise text,
    latitude_wgs84 double precision,
    longitude_wgs84 double precision,
    date_mise_service date,
    date_mise_hors_service date,
    source_file text,
    first_seen_year integer,
    last_seen_year integer
);

CREATE TABLE IF NOT EXISTS ode_fact.fact_steu (
    year_reference integer NOT NULL,
    code_steu text NOT NULL REFERENCES ode_ref.dim_steu(code_steu),
    code_agglo text,
    etat_steu text,
    capacite_nominale_eh double precision,
    capacite_nominale_kg_dbo5 double precision,
    percentile95_m3_j double precision,
    charge_max_entree_eh double precision,
    debit_entrant_m3_j double precision,
    filiere_eau_principale text,
    filiere_boues_principale text,
    conformite_collecte_agglo text,
    conformite_equipement_agglo text,
    conformite_performance_agglo text,
    conformite_globale_agglo text,
    conformite_equipement_steu text,
    conformite_performance_steu text,
    conformite_station_reconstituee boolean,
    cause_non_conformite text,
    production_boues_tms double precision,
    code_systeme_collecte text,
    nom_systeme_collecte text,
    code_masse_eau text,
    nom_masse_eau text,
    nom_milieu_rejet text,
    type_milieu_rejet text,
    date_derniere_modification_source date,
    source_file text NOT NULL,
    import_timestamp timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (year_reference, code_steu)
);

CREATE TABLE IF NOT EXISTS ode_fact.fact_agglo_assainissement (
    year_reference integer NOT NULL,
    code_agglo text NOT NULL,
    nom_agglo text,
    commune_principale text,
    code_insee_commune_principale text,
    etat_agglo text,
    taille_agglo_eh double precision,
    maximum_pollutions_entrantes_eh double precision,
    somme_capacites_nominales_eh double precision,
    conformite_equipement_agglo text,
    conformite_performance_agglo text,
    conformite_collecte_temps_sec text,
    conformite_globale_agglo text,
    date_mise_a_jour_agglo date,
    type_reseau_majoritaire text,
    source_file text NOT NULL,
    PRIMARY KEY (year_reference, code_agglo)
);

CREATE TABLE IF NOT EXISTS ode_etl.data_quality_issue (
    issue_id bigserial PRIMARY KEY,
    year_reference integer,
    code_steu text,
    severity text NOT NULL,
    issue_type text NOT NULL,
    field_name text,
    observed_value text,
    message text NOT NULL,
    source_file text,
    detected_at timestamptz NOT NULL DEFAULT now()
);
