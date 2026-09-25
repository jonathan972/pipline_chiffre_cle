CREATE SCHEMA IF NOT EXISTS ode_sispea;

CREATE TABLE IF NOT EXISTS ode_sispea.dim_service (
    annee_reference integer NOT NULL,
    competence varchar(8) NOT NULL,
    service_id varchar(64) NOT NULL,
    nom_service text,
    collectivite text,
    epci_normalise varchar(32),
    statut text,
    mode_gestion text,
    operateur text,
    source_file text,
    date_snapshot timestamp,
    source_sha256 char(64),
    PRIMARY KEY (annee_reference, competence, service_id)
);

CREATE TABLE IF NOT EXISTS ode_sispea.fact_service_long (
    annee_reference integer NOT NULL,
    competence varchar(8) NOT NULL,
    service_id varchar(64) NOT NULL,
    epci_normalise varchar(32),
    code varchar(32) NOT NULL,
    valeur_num double precision,
    valeur_texte text,
    source_file text,
    date_snapshot timestamp,
    PRIMARY KEY (annee_reference, competence, service_id, code)
);

CREATE TABLE IF NOT EXISTS ode_sispea.fact_consolidee (
    annee_reference integer NOT NULL,
    competence varchar(8) NOT NULL,
    code varchar(32) NOT NULL,
    libelle text,
    unite text,
    min double precision,
    max double precision,
    valeur_consolidee double precision,
    nombre_donnees_utilisees integer,
    source_file text,
    date_snapshot timestamp,
    PRIMARY KEY (annee_reference, competence, code)
);

CREATE TABLE IF NOT EXISTS ode_sispea.data_quality_issue (
    issue_id bigserial PRIMARY KEY,
    annee_reference integer,
    competence varchar(8),
    severity varchar(16),
    issue_type varchar(64),
    message text,
    source_file text,
    created_at timestamptz DEFAULT now()
);
